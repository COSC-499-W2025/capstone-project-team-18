"""
Minimal model-runtime compatibility layer for branches using Azure provider.
"""

from __future__ import annotations

from typing import Any


def cuda_available() -> bool:
    return False


def get_causal_lm(_model_name: str) -> tuple[Any | None, Any | None]:
    return None, None


def get_zero_shot_pipeline(_model_name: str) -> Any | None:
    return None
