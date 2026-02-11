"""
Helpers for running structured JSON generation with llama-cpp-python.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_LOCK = threading.Lock()
_MODEL_CACHE: dict[str, Any] = {}
_MODEL_FAILED: set[str] = set()
_DEFAULT_GGUF_CANDIDATES = (
    "models/phi-4-mini-q4_k_m.gguf",
    "models/phi-4-mini-q4-k-m.gguf",
    "ollama/phi-4-mini-q4_k_m.gguf",
    "ollama/phi-4-mini-q4-k-m.gguf",
    "phi-4-mini-q4_k_m.gguf",
    "phi-4-mini-q4-k-m.gguf",
)


def _truthy(raw: str | None) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _resolve_existing_env_path(var_name: str) -> str | None:
    raw = os.environ.get(var_name)
    if not raw:
        return None
    resolved = _resolve_path(raw)
    if resolved.exists() and resolved.is_file():
        return str(resolved.resolve())
    return None


def _resolve_configured_env_path(var_name: str) -> str | None:
    raw = os.environ.get(var_name)
    if not raw:
        return None
    return str(_resolve_path(raw))


def _auto_discovered_model_path() -> str | None:
    for candidate in _DEFAULT_GGUF_CANDIDATES:
        resolved = _resolve_path(candidate)
        if resolved.exists() and resolved.is_file():
            return str(resolved.resolve())
    return None


def llama_cpp_enabled() -> bool:
    """Return whether llama-cpp backend is enabled."""
    explicit = os.environ.get("ARTIFACT_MINER_USE_LLAMA_CPP")
    if explicit is not None:
        return _truthy(explicit)

    # Auto-enable when a GGUF file is discoverable locally.
    return resolve_llama_cpp_model_path("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH") is not None


def resolve_llama_cpp_model_path(model_env_var: str) -> str | None:
    """
    Resolve model path using:
    1) per-feature override env
    2) global override env
    3) local auto-discovery candidates

    Explicit env paths are returned even when missing so callers can emit an
    actionable "path not found" message.
    """
    explicit_existing = _resolve_existing_env_path(model_env_var)
    if explicit_existing:
        return explicit_existing
    explicit_global_existing = _resolve_existing_env_path("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH")
    if explicit_global_existing:
        return explicit_global_existing

    explicit_configured = _resolve_configured_env_path(model_env_var)
    if explicit_configured:
        return explicit_configured
    explicit_global_configured = _resolve_configured_env_path("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH")
    if explicit_global_configured:
        return explicit_global_configured

    return _auto_discovered_model_path()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return _truthy(raw)


def _load_model(model_path: str) -> Any | None:
    """
    Load llama-cpp model once per process and cache by model path.
    """
    with _LOCK:
        cached = _MODEL_CACHE.get(model_path)
        if cached is not None:
            return cached
        if model_path in _MODEL_FAILED:
            return None

    try:
        from llama_cpp import Llama
    except Exception:
        logger.info("llama-cpp-python is not installed; skipping llama-cpp backend")
        with _LOCK:
            _MODEL_FAILED.add(model_path)
        return None

    try:
        model_file = _resolve_path(model_path)
        if not model_file.exists() or not model_file.is_file():
            logger.warning("llama-cpp model path does not exist: %s", model_path)
            with _LOCK:
                _MODEL_FAILED.add(model_path)
            return None

        n_ctx = max(512, _env_int("ARTIFACT_MINER_LLAMA_CPP_N_CTX", 4096))
        cpu_count = os.cpu_count() or 4
        max_threads = max(1, _env_int("ARTIFACT_MINER_LLAMA_CPP_MAX_THREADS", 8))
        requested_threads = max(
            1,
            _env_int("ARTIFACT_MINER_LLAMA_CPP_N_THREADS", min(6, cpu_count)),
        )
        n_threads = min(requested_threads, max_threads, cpu_count)
        n_batch = max(32, _env_int("ARTIFACT_MINER_LLAMA_CPP_N_BATCH", 256))
        n_gpu_layers = _env_int("ARTIFACT_MINER_LLAMA_CPP_N_GPU_LAYERS", 0)
        use_mmap = _env_bool("ARTIFACT_MINER_LLAMA_CPP_USE_MMAP", True)
        use_mlock = _env_bool("ARTIFACT_MINER_LLAMA_CPP_USE_MLOCK", False)
        seed = _env_int("ARTIFACT_MINER_LLAMA_CPP_SEED", 42)

        logger.info("Loading llama-cpp summary model from: %s", model_file)
        model = Llama(
            model_path=str(model_file),
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=n_batch,
            n_gpu_layers=n_gpu_layers,
            use_mmap=use_mmap,
            use_mlock=use_mlock,
            seed=seed,
            verbose=False,
        )
        with _LOCK:
            _MODEL_CACHE[model_path] = model
        return model
    except Exception:
        logger.exception("Failed to load llama-cpp model from %s", model_path)
        with _LOCK:
            _MODEL_FAILED.add(model_path)
        return None


def _generate_raw_completion(
    model_path: str,
    prompt: str,
    *,
    max_tokens: int,
    temperature: float,
    top_p: float,
    stop: list[str] | None = None,
) -> str | None:
    """
    Generate plain text from a local GGUF model via llama-cpp.
    """
    model = _load_model(model_path)
    if model is None:
        return None

    try:
        response = model.create_completion(
            prompt=prompt,
            max_tokens=max(16, int(max_tokens)),
            temperature=max(0.0, float(temperature)),
            top_p=max(0.0, min(1.0, float(top_p))),
            stop=stop or [],
            echo=False,
        )
        choices = response.get("choices", [])
        if not choices:
            return None
        text = choices[0].get("text", "")
        if not isinstance(text, str):
            return None
        return text.strip()
    except Exception:
        logger.debug("llama-cpp generation failed", exc_info=True)
        return None


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """
    Parse a JSON object from output, including noisy wrappers.
    """
    if not raw_text:
        return None

    decoder = json.JSONDecoder()
    text = raw_text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(text[idx:])
        except Exception:
            continue
        if isinstance(candidate, dict):
            return candidate
    return None


def llama_cpp_generate_json_object(
    model_path: str,
    prompt: str,
    *,
    validator: Callable[[dict[str, Any]], tuple[bool, str]] | None = None,
    max_retries: int = 2,
    max_tokens: int = 240,
    temperature: float = 0.0,
    top_p: float = 0.9,
    stop: list[str] | None = None,
    max_total_seconds: float | None = None,
) -> dict[str, Any] | None:
    """
    Generate one JSON object with correction retries when validation fails.
    """
    if not model_path:
        return None

    attempts = max(1, int(max_retries) + 1)
    started_at = perf_counter()
    last_error = "invalid_json"

    for attempt in range(attempts):
        if max_total_seconds is not None and (perf_counter() - started_at) > float(max_total_seconds):
            logger.warning(
                "llama-cpp JSON generation exceeded budget (%.1fs); aborting retries",
                perf_counter() - started_at,
            )
            break

        attempt_prompt = prompt
        if attempt > 0:
            attempt_prompt = (
                f"{prompt}\n\n"
                "The previous output was invalid.\n"
                f"Validation reason: {last_error}\n"
                "Return exactly one JSON object with no extra text."
            )

        raw = _generate_raw_completion(
            model_path=model_path,
            prompt=attempt_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop,
        )
        if not raw:
            last_error = "empty_response"
            continue

        payload = _extract_json_object(raw)
        if payload is None:
            last_error = "invalid_json"
            continue

        if validator is None:
            return payload

        is_valid, reason = validator(payload)
        if is_valid:
            return payload
        last_error = reason

    return None


def llama_cpp_generate_text(
    model_path: str,
    prompt: str,
    *,
    max_retries: int = 0,
    max_tokens: int = 240,
    temperature: float = 0.0,
    top_p: float = 0.9,
    stop: list[str] | None = None,
    max_total_seconds: float | None = None,
) -> str | None:
    """
    Generate plain text with optional retries and a total runtime budget.
    """
    if not model_path:
        return None

    attempts = max(1, int(max_retries) + 1)
    started_at = perf_counter()

    for attempt in range(attempts):
        if max_total_seconds is not None and (perf_counter() - started_at) > float(max_total_seconds):
            logger.warning(
                "llama-cpp text generation exceeded budget (%.1fs); aborting retries",
                perf_counter() - started_at,
            )
            break

        attempt_prompt = prompt
        if attempt > 0:
            attempt_prompt = (
                f"{prompt}\n\n"
                "The previous output was invalid.\n"
                "Return only the final summary text with no preamble."
            )

        raw = _generate_raw_completion(
            model_path=model_path,
            prompt=attempt_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop,
        )
        if raw:
            return raw.strip()

    return None


def warmup_llama_cpp_model(model_path: str) -> bool:
    """
    Run a tiny completion so model pages are mapped before first user request.
    """
    raw = _generate_raw_completion(
        model_path=model_path,
        prompt='Return {"ok": true}',
        max_tokens=24,
        temperature=0.0,
        top_p=1.0,
    )
    return raw is not None
