from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _extract_message_content(parsed: dict[str, Any], schema_name: str) -> str | None:
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
    return content.strip()


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def _log_malformed_json(schema_name: str, content: str, exc: Exception) -> None:
    preview = content[:500]
    suffix = content[-500:] if len(content) > 500 else content
    logger.error(
        "Azure OpenAI returned malformed JSON for schema=%s (length=%s, preview=%r, suffix=%r, error=%s)",
        schema_name,
        len(content),
        preview,
        suffix,
        exc,
    )


def _parse_json_object_content(content: str, schema_name: str) -> dict[str, Any] | None:
    try:
        parsed_content = json.loads(content)
        return parsed_content if isinstance(parsed_content, dict) else None
    except json.JSONDecodeError as exc:
        candidate = _extract_first_json_object(content)
        if candidate and candidate != content:
            try:
                parsed_content = json.loads(candidate)
                if isinstance(parsed_content, dict):
                    logger.warning(
                        "Recovered malformed Azure OpenAI JSON for schema=%s by extracting the first balanced object",
                        schema_name,
                    )
                    return parsed_content
            except json.JSONDecodeError:
                pass
        _log_malformed_json(schema_name, content, exc)
        return None


def _parse_model_content(content: str, schema_name: str, response_model: type[BaseModel]) -> BaseModel | None:
    candidate = content
    try:
        return _model_validate_json(response_model, candidate)
    except Exception as exc:
        extracted = _extract_first_json_object(content)
        if extracted and extracted != content:
            try:
                model = _model_validate_json(response_model, extracted)
                logger.warning(
                    "Recovered malformed Azure OpenAI model output for schema=%s by extracting the first balanced object",
                    schema_name,
                )
                return model
            except Exception:
                pass
        _log_malformed_json(schema_name, content, exc)
        return None


def _request_payload(
    *,
    system_prompt: str,
    user_prompt: str,
    response_format: dict[str, Any],
    max_tokens: int,
    temperature: float,
) -> bytes:
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": max(0.0, float(temperature)),
        "max_tokens": max(32, int(max_tokens)),
        "response_format": response_format,
    }
    return json.dumps(payload).encode("utf-8")


def _make_request(body: bytes, deployment: str | None) -> dict[str, Any] | None:
    request = urllib.request.Request(
        url=_request_url(deployment),
        data=body,
        headers={
            "Content-Type": "application/json",
            "api-key": os.environ["AZURE_OPENAI_API_KEY"].strip(),
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45.0) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _retry_delay_seconds(attempt: int, *, rate_limited: bool = False) -> float:
    return (1.5 if rate_limited else 0.4) * (attempt + 1)


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

    body = _request_payload(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": _model_schema(response_model),
            },
        },
    )

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            parsed = _make_request(body, deployment)
            if parsed is None:
                return None
            content = _extract_message_content(parsed, schema_name)
            if content is None:
                return None
            model = _parse_model_content(content, schema_name, response_model)
            if model is not None:
                return model
            if attempt + 1 < max_attempts:
                logger.warning("Retrying Azure OpenAI parse for schema=%s after malformed structured output", schema_name)
                time.sleep(_retry_delay_seconds(attempt))
        except urllib.error.HTTPError as exc:
            logger.error(
                "Azure OpenAI HTTP error for schema=%s (status=%s)",
                schema_name,
                getattr(exc, "code", "unknown"),
            )
            if getattr(exc, "code", None) == 429 and attempt + 1 < max_attempts:
                logger.warning("Retrying Azure OpenAI request for schema=%s after rate limiting", schema_name)
                time.sleep(_retry_delay_seconds(attempt, rate_limited=True))
                continue
            return None
        except (urllib.error.URLError, OSError, TimeoutError):
            logger.exception("Azure OpenAI request failed for schema=%s", schema_name)
            if attempt + 1 < max_attempts:
                time.sleep(_retry_delay_seconds(attempt))
                continue
            return None
        except Exception:
            logger.exception("Azure OpenAI response parsing failed for schema=%s", schema_name)
            if attempt + 1 < max_attempts:
                time.sleep(_retry_delay_seconds(attempt))
                continue
            return None
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

    body = _request_payload(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": _normalize_schema_for_azure(response_schema),
            },
        },
    )

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            parsed = _make_request(body, deployment)
            if parsed is None:
                return None
            content = _extract_message_content(parsed, schema_name)
            if content is None:
                return None
            parsed_content = _parse_json_object_content(content, schema_name)
            if parsed_content is not None:
                return parsed_content
            if attempt + 1 < max_attempts:
                logger.warning("Retrying Azure OpenAI JSON parse for schema=%s after malformed structured output", schema_name)
                time.sleep(_retry_delay_seconds(attempt))
        except urllib.error.HTTPError as exc:
            logger.error(
                "Azure OpenAI HTTP error for schema=%s (status=%s)",
                schema_name,
                getattr(exc, "code", "unknown"),
            )
            if getattr(exc, "code", None) == 429 and attempt + 1 < max_attempts:
                logger.warning("Retrying Azure OpenAI request for schema=%s after rate limiting", schema_name)
                time.sleep(_retry_delay_seconds(attempt, rate_limited=True))
                continue
            return None
        except (urllib.error.URLError, OSError, TimeoutError):
            logger.exception("Azure OpenAI request failed for schema=%s", schema_name)
            if attempt + 1 < max_attempts:
                time.sleep(_retry_delay_seconds(attempt))
                continue
            return None
        except Exception:
            logger.exception("Azure OpenAI response parsing failed for schema=%s", schema_name)
            if attempt + 1 < max_attempts:
                time.sleep(_retry_delay_seconds(attempt))
                continue
            return None
    return None
