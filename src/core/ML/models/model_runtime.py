"""
Shared runtime helpers for loading and caching heavyweight ML models.

This module prevents duplicate model initialization across feature modules
that use the same underlying Hugging Face models.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_LOCK = threading.Lock()

_CAUSAL_LM_CACHE: dict[tuple[str, str], tuple[Any, Any]] = {}
_CAUSAL_LM_FAILED: set[tuple[str, str]] = set()

_ZSC_PIPELINE_CACHE: dict[tuple[str, str], Any] = {}
_ZSC_PIPELINE_FAILED: set[tuple[str, str]] = set()


def _truthy(raw: str | None) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def cuda_available() -> bool:
    """Return whether CUDA is available without hard import-time dependency."""
    try:
        import torch
    except ImportError:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _local_files_only() -> bool:
    """
    Respect offline/cache-only settings to avoid repeated network stalls.
    """
    return (
        os.environ.get("ARTIFACT_MINER_LOCAL_FILES_ONLY") == "1"
        or os.environ.get("HF_HUB_OFFLINE") == "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )


def _zero_shot_server_url() -> str | None:
    """
    Resolve optional remote zero-shot inference server URL.
    """
    raw = (
        os.environ.get("ARTIFACT_MINER_ZERO_SHOT_SERVER_URL")
        or os.environ.get("ARTIFACT_MINER_ML_SERVER_URL")
    )
    if not raw:
        return None
    cleaned = raw.strip().rstrip("/")
    if not cleaned:
        return None
    return cleaned


def _zero_shot_server_timeout_seconds() -> float:
    raw = os.environ.get("ARTIFACT_MINER_ZERO_SHOT_SERVER_TIMEOUT_SEC", "45")
    try:
        return max(1.0, float(raw))
    except (TypeError, ValueError):
        return 45.0


def _zero_shot_server_required() -> bool:
    """
    When true, do not fall back to local transformers if remote server is down.
    """
    return _truthy(os.environ.get("ARTIFACT_MINER_ZERO_SHOT_SERVER_REQUIRED"))


def _http_json_request(
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float,
) -> dict[str, Any] | None:
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("ARTIFACT_MINER_ZERO_SHOT_SERVER_API_KEY")
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    data = None
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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
        logger.debug("Zero-shot HTTP request failed: %s", url, exc_info=True)
    return None


def _zero_shot_server_ready(server_url: str) -> bool:
    payload = _http_json_request(
        f"{server_url}/health",
        timeout=min(10.0, _zero_shot_server_timeout_seconds()),
    )
    if not isinstance(payload, dict):
        return False
    if payload.get("ok") is True:
        return True
    return str(payload.get("status", "")).lower() in {"ok", "ready"}


class _RemoteZeroShotPipeline:
    """
    Drop-in callable adapter that mimics transformers zero-shot pipeline output.
    """

    def __init__(self, model_name: str, server_url: str):
        self.model_name = model_name
        self.server_url = server_url

    def __call__(
        self,
        sequences: str | list[str],
        candidate_labels: list[str],
        *,
        multi_label: bool = False,
        batch_size: int | None = None,
        hypothesis_template: str | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        single_input = isinstance(sequences, str)
        if single_input:
            normalized_sequences = [sequences]
        elif isinstance(sequences, list):
            normalized_sequences = [str(item) for item in sequences]
        else:
            raise TypeError("sequences must be a string or a list of strings")

        labels = [str(label).strip() for label in candidate_labels if str(label).strip()]
        if not labels:
            raise ValueError("candidate_labels must not be empty")

        payload: dict[str, Any] = {
            "model": self.model_name,
            "inputs": normalized_sequences,
            "candidate_labels": labels,
            "multi_label": bool(multi_label),
        }
        if batch_size is not None:
            try:
                payload["batch_size"] = max(1, int(batch_size))
            except (TypeError, ValueError):
                pass
        if hypothesis_template:
            payload["hypothesis_template"] = str(hypothesis_template)

        response = _http_json_request(
            f"{self.server_url}/v1/zero-shot/classify",
            payload=payload,
            timeout=_zero_shot_server_timeout_seconds(),
        )
        if not isinstance(response, dict):
            raise RuntimeError("Zero-shot server returned an empty response")

        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            raise RuntimeError("Zero-shot server response missing results list")
        if len(raw_results) != len(normalized_sequences):
            raise RuntimeError("Zero-shot server returned unexpected result count")

        normalized_results: list[dict[str, Any]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                raise RuntimeError("Zero-shot server returned malformed result item")
            raw_labels = item.get("labels")
            raw_scores = item.get("scores")
            if not isinstance(raw_labels, list) or not isinstance(raw_scores, list):
                raise RuntimeError("Zero-shot server result is missing labels/scores")
            if len(raw_labels) != len(raw_scores):
                raise RuntimeError("Zero-shot server labels/scores length mismatch")

            labels_out = [str(label) for label in raw_labels]
            try:
                scores_out = [float(score) for score in raw_scores]
            except (TypeError, ValueError) as exc:
                raise RuntimeError("Zero-shot server returned non-numeric scores") from exc

            normalized_results.append({
                "labels": labels_out,
                "scores": scores_out,
            })

        if single_input:
            return normalized_results[0]
        return normalized_results


def get_causal_lm(model_name: str) -> tuple[Any | None, Any | None]:
    """
    Load and cache a CausalLM + tokenizer pair by model and device profile.
    Returns (None, None) after the first failure for the same key.
    """
    device_profile = "cuda" if cuda_available() else "cpu"
    key = (model_name, device_profile)

    with _LOCK:
        cached = _CAUSAL_LM_CACHE.get(key)
        if cached is not None:
            return cached
        if key in _CAUSAL_LM_FAILED:
            return None, None

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        logger.info("ML dependencies are not installed; skipping CausalLM load")
        with _LOCK:
            _CAUSAL_LM_FAILED.add(key)
        return None, None

    try:
        local_only = _local_files_only()
        use_cuda = torch.cuda.is_available()
        dtype = torch.float16 if use_cuda else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            use_fast=True,
            local_files_only=local_only,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            local_files_only=local_only,
        )
        if use_cuda:
            model = model.to("cuda")

        with _LOCK:
            _CAUSAL_LM_CACHE[key] = (model, tokenizer)
        return model, tokenizer
    except Exception:
        logger.exception(
            "Failed to load CausalLM %s (%s)",
            model_name,
            device_profile,
        )
        with _LOCK:
            _CAUSAL_LM_FAILED.add(key)
        return None, None


def get_zero_shot_pipeline(model_name: str) -> Any | None:
    """
    Load and cache a zero-shot pipeline by model name.
    Returns None after the first failure for the same model.
    """
    server_url = _zero_shot_server_url()
    if server_url:
        remote_key = (model_name, f"remote:{server_url}")
        with _LOCK:
            cached = _ZSC_PIPELINE_CACHE.get(remote_key)
            if cached is not None:
                return cached
            remote_failed = remote_key in _ZSC_PIPELINE_FAILED

        if not remote_failed:
            if _zero_shot_server_ready(server_url):
                classifier = _RemoteZeroShotPipeline(model_name=model_name, server_url=server_url)
                with _LOCK:
                    _ZSC_PIPELINE_CACHE[remote_key] = classifier
                logger.info("Using remote zero-shot server for model: %s", model_name)
                return classifier

            logger.warning(
                "Zero-shot server unavailable at %s; %s",
                server_url,
                "remote-only mode enabled" if _zero_shot_server_required() else "falling back to local pipeline",
            )
            with _LOCK:
                _ZSC_PIPELINE_FAILED.add(remote_key)
            if _zero_shot_server_required():
                return None

    local_key = (model_name, "local")
    with _LOCK:
        cached = _ZSC_PIPELINE_CACHE.get(local_key)
        if cached is not None:
            return cached
        if local_key in _ZSC_PIPELINE_FAILED:
            return None

    try:
        from transformers import pipeline
    except ImportError:
        logger.info("Transformers is not installed; skipping zero-shot pipeline")
        with _LOCK:
            _ZSC_PIPELINE_FAILED.add(local_key)
        return None

    try:
        local_only = _local_files_only()
        classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            local_files_only=local_only,
        )
        with _LOCK:
            _ZSC_PIPELINE_CACHE[local_key] = classifier
        return classifier
    except Exception:
        logger.exception("Failed to initialize zero-shot pipeline: %s", model_name)
        with _LOCK:
            _ZSC_PIPELINE_FAILED.add(local_key)
        return None
