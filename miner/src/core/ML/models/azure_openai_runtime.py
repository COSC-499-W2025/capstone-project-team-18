from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def azure_openai_enabled() -> bool:
    """Return whether Azure OpenAI is the active ML provider."""
    return os.environ.get("ARTIFACT_MINER_ML_PROVIDER", "").strip().lower() == "azure_openai"


def _config_valid(deployment: str | None = None) -> bool:
    return bool(
        os.environ.get("AZURE_OPENAI_ENDPOINT")
        and os.environ.get("AZURE_OPENAI_API_KEY")
        and os.environ.get("AZURE_OPENAI_API_VERSION")
        and ((deployment or "").strip() or os.environ.get("AZURE_OPENAI_DEPLOYMENT"))
    )


def _request_url(deployment: str | None = None) -> str:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
    active_deployment = (deployment or os.environ["AZURE_OPENAI_DEPLOYMENT"]).strip()
    api_version = os.environ["AZURE_OPENAI_API_VERSION"].strip()
    return f"{endpoint}/openai/deployments/{active_deployment}/chat/completions?api-version={api_version}"


def _model_schema(model: type[BaseModel]) -> dict[str, Any]:
    if hasattr(model, "model_json_schema"):
        schema = model.model_json_schema()
    else:
        schema = model.schema()  # pragma: no cover - pydantic v1 fallback
    return _normalize_schema_for_azure(schema)


def _normalize_schema_for_azure(node: Any) -> Any:
    """
    Azure structured outputs require object schemas to explicitly set
    additionalProperties=false. Apply recursively across schema nodes.
    """
    if isinstance(node, dict):
        normalized: dict[str, Any] = {k: _normalize_schema_for_azure(v) for k, v in node.items()}
        is_object = normalized.get("type") == "object" or "properties" in normalized
        if is_object:
            normalized["additionalProperties"] = False
        # Recurse for dictionary-valued additionalProperties if present in input schema.
        if isinstance(node.get("additionalProperties"), dict):
            normalized["additionalProperties"] = _normalize_schema_for_azure(node["additionalProperties"])
        return normalized
    if isinstance(node, list):
        return [_normalize_schema_for_azure(item) for item in node]
    return node


def _model_validate_json(model: type[BaseModel], text: str) -> BaseModel:
    if hasattr(model, "model_validate_json"):
        return model.model_validate_json(text)
    return model.parse_raw(text)  # pragma: no cover - pydantic v1 fallback


def azure_chat_parse(
    *,
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    schema_name: str,
    max_tokens: int = 280,
    temperature: float = 0.0,
    deployment: str | None = None,
) -> BaseModel | None:
    """
    Request a structured JSON response from Azure OpenAI and parse to Pydantic.
    """
    if not azure_openai_enabled():
        return None
    if not _config_valid(deployment):
        logger.warning("Azure OpenAI provider selected but required env vars are missing")
        return None

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": max(0.0, float(temperature)),
        "max_tokens": max(32, int(max_tokens)),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": _model_schema(response_model),
            },
        },
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=_request_url(deployment),
        data=body,
        headers={
            "Content-Type": "application/json",
            "api-key": os.environ["AZURE_OPENAI_API_KEY"].strip(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45.0) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        choices = parsed.get("choices", [])
        if not choices:
            logger.warning("Azure OpenAI returned no choices for schema=%s", schema_name)
            return None
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, list):
            # Some responses return a list of content parts.
            content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            logger.warning("Azure OpenAI returned empty content for schema=%s", schema_name)
            return None
        return _model_validate_json(response_model, content.strip())
    except urllib.error.HTTPError as exc:
        logger.error(
            "Azure OpenAI HTTP error for schema=%s (status=%s)",
            schema_name,
            getattr(exc, "code", "unknown"),
        )
    except (urllib.error.URLError, OSError, TimeoutError):
        logger.exception("Azure OpenAI request failed for schema=%s", schema_name)
    except Exception:
        logger.exception("Azure OpenAI response parsing failed for schema=%s", schema_name)
    return None


def azure_chat_json(
    *,
    system_prompt: str,
    user_prompt: str,
    response_schema: dict[str, Any],
    schema_name: str,
    max_tokens: int = 280,
    temperature: float = 0.0,
    deployment: str | None = None,
) -> dict[str, Any] | None:
    """
    Request a structured JSON response from Azure OpenAI and parse to a dict.
    """
    if not azure_openai_enabled():
        return None
    if not _config_valid(deployment):
        logger.warning("Azure OpenAI provider selected but required env vars are missing")
        return None

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": max(0.0, float(temperature)),
        "max_tokens": max(32, int(max_tokens)),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": _normalize_schema_for_azure(response_schema),
            },
        },
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=_request_url(deployment),
        data=body,
        headers={
            "Content-Type": "application/json",
            "api-key": os.environ["AZURE_OPENAI_API_KEY"].strip(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45.0) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        choices = parsed.get("choices", [])
        if not choices:
            logger.warning("Azure OpenAI returned no choices for schema=%s", schema_name)
            return None
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            logger.warning("Azure OpenAI returned empty content for schema=%s", schema_name)
            return None
        parsed_content = json.loads(content.strip())
        return parsed_content if isinstance(parsed_content, dict) else None
    except urllib.error.HTTPError as exc:
        logger.error(
            "Azure OpenAI HTTP error for schema=%s (status=%s)",
            schema_name,
            getattr(exc, "code", "unknown"),
        )
    except (urllib.error.URLError, OSError, TimeoutError):
        logger.exception("Azure OpenAI request failed for schema=%s", schema_name)
    except Exception:
        logger.exception("Azure OpenAI response parsing failed for schema=%s", schema_name)
    return None
