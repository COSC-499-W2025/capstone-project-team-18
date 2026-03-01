from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel

from src.core.ML.models.azure_openai_runtime import azure_openai_enabled
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


class AzureFoundryManager:
    """
    Lightweight manager for structured Azure OpenAI/Foundry chat responses.
    """

    def __init__(self):
        self.endpoint = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
        self.api_key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
        self.api_version = (os.environ.get("AZURE_OPENAI_API_VERSION") or "").strip()
        self.deployment = (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip()

    def _configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.api_version and self.deployment)

    def _url(self) -> str:
        return (
            f"{self.endpoint}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )

    def _model_schema(self, model: type[BaseModel]) -> dict[str, Any]:
        schema = model.model_json_schema() if hasattr(model, "model_json_schema") else model.schema()
        return self._normalize_schema_for_azure(schema)

    def _normalize_schema_for_azure(self, node: Any) -> Any:
        if isinstance(node, dict):
            normalized = {k: self._normalize_schema_for_azure(v) for k, v in node.items()}
            is_object = normalized.get("type") == "object" or "properties" in normalized
            if is_object:
                normalized["additionalProperties"] = False
            if isinstance(node.get("additionalProperties"), dict):
                normalized["additionalProperties"] = self._normalize_schema_for_azure(node["additionalProperties"])
            return normalized
        if isinstance(node, list):
            return [self._normalize_schema_for_azure(item) for item in node]
        return node

    def process_request(
        self,
        *,
        user_input: str,
        system_prompt: str,
        response_model: type[BaseModel],
        schema_name: str | None = None,
        max_tokens: int = 220,
        temperature: float = 0.0,
    ) -> BaseModel | None:
        if not azure_openai_enabled():
            return None
        if not self._configured():
            logger.warning("AzureFoundryManager missing required AZURE_OPENAI_* configuration")
            return None

        schema_id = schema_name or response_model.__name__.lower()
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            "temperature": max(0.0, float(temperature)),
            "max_tokens": max(32, int(max_tokens)),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_id,
                    "strict": True,
                    "schema": self._model_schema(response_model),
                },
            },
        }

        request = urllib.request.Request(
            url=self._url(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=45.0) as response:
                raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            choices = parsed.get("choices", [])
            if not choices:
                return None
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content")
            if isinstance(content, list):
                content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
            if not isinstance(content, str) or not content.strip():
                return None
            if hasattr(response_model, "model_validate_json"):
                return response_model.model_validate_json(content.strip())
            return response_model.parse_raw(content.strip())  # pragma: no cover
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            logger.error(
                "AzureFoundryManager HTTP error (schema=%s, status=%s, body=%s)",
                schema_id,
                getattr(exc, "code", "unknown"),
                body[:300],
            )
        except Exception:
            logger.exception("AzureFoundryManager request failed (schema=%s)", schema_id)
        return None
