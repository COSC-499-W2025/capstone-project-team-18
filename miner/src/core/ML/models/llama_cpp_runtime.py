"""
Minimal llama-cpp runtime compatibility layer for Azure-first branches.
"""

from __future__ import annotations

from typing import Any, Callable


def llama_cpp_enabled() -> bool:
    return False


def resolve_llama_cpp_model_path(_model_env_var: str) -> str | None:
    return None


def llama_cpp_generate_json_object(
    _model_path: str,
    _prompt: str,
    *,
    validator: Callable[[dict[str, Any]], tuple[bool, str]] | None = None,
    max_retries: int = 2,
    max_tokens: int = 240,
    temperature: float = 0.0,
    top_p: float = 0.9,
    stop: list[str] | None = None,
    max_total_seconds: float | None = None,
) -> dict[str, Any] | None:
    return None


def llama_cpp_generate_text(
    _model_path: str,
    _prompt: str,
    *,
    max_retries: int = 0,
    max_tokens: int = 240,
    temperature: float = 0.0,
    top_p: float = 0.9,
    stop: list[str] | None = None,
    max_total_seconds: float | None = None,
) -> str | None:
    return None


def warmup_llama_cpp_model(_model_path: str) -> bool:
    return False
