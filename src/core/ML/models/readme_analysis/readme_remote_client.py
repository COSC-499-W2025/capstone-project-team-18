from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _truthy(raw: str | None) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _readme_remote_disabled() -> bool:
    return _truthy(os.environ.get("ARTIFACT_MINER_README_REMOTE_DISABLE"))


def _readme_server_url() -> str | None:
    if _readme_remote_disabled():
        return None
    raw = (
        os.environ.get("ARTIFACT_MINER_README_SERVER_URL")
        or os.environ.get("ARTIFACT_MINER_ML_SERVER_URL")
        or os.environ.get("ARTIFACT_MINER_ZERO_SHOT_SERVER_URL")
    )
    if not raw:
        return None
    cleaned = raw.strip().rstrip("/")
    return cleaned or None


def _timeout_seconds() -> float:
    raw = os.environ.get("ARTIFACT_MINER_README_SERVER_TIMEOUT_SEC", "45")
    try:
        return max(1.0, float(raw))
    except (TypeError, ValueError):
        return 45.0


def _server_required() -> bool:
    return _truthy(os.environ.get("ARTIFACT_MINER_README_SERVER_REQUIRED"))


def _http_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=_timeout_seconds()) as response:
            body = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return parsed
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        OSError,
        TimeoutError,
        json.JSONDecodeError,
    ):
        logger.debug("README remote request failed: %s", url, exc_info=True)
    return None


def remote_extract_keyphrases(text: str, top_n: int) -> list[str] | None:
    server = _readme_server_url()
    if not server:
        return [] if _server_required() else None
    payload = _http_post_json(
        f"{server}/v1/readme/keyphrases",
        {
            "text": text,
            "top_n": int(max(1, top_n)),
        },
    )
    if not isinstance(payload, dict):
        return [] if _server_required() else None
    phrases = payload.get("keyphrases")
    if not isinstance(phrases, list):
        return [] if _server_required() else None
    return [str(item).strip() for item in phrases if str(item).strip()]


def remote_extract_themes_bulk(texts: list[str], max_themes: int) -> list[list[str]] | None:
    server = _readme_server_url()
    if not server:
        return [[] for _ in texts] if _server_required() else None
    payload = _http_post_json(
        f"{server}/v1/readme/themes/bulk",
        {
            "texts": texts,
            "max_themes": int(max(1, max_themes)),
        },
    )
    if not isinstance(payload, dict):
        return [[] for _ in texts] if _server_required() else None
    themes = payload.get("themes")
    if not isinstance(themes, list):
        return [[] for _ in texts] if _server_required() else None
    normalized: list[list[str]] = []
    for item in themes:
        if isinstance(item, list):
            normalized.append([str(term).strip() for term in item if str(term).strip()])
        else:
            normalized.append([])
    if len(normalized) != len(texts):
        return [[] for _ in texts] if _server_required() else None
    return normalized
