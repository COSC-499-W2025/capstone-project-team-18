"""
Shared runtime helpers for loading and caching heavyweight ML models.

This module prevents duplicate model initialization across feature modules
that use the same underlying Hugging Face models.
"""

from __future__ import annotations

import os
import threading
from typing import Any

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_LOCK = threading.Lock()

_CAUSAL_LM_CACHE: dict[tuple[str, str], tuple[Any, Any]] = {}
_CAUSAL_LM_FAILED: set[tuple[str, str]] = set()

_ZSC_PIPELINE_CACHE: dict[str, Any] = {}
_ZSC_PIPELINE_FAILED: set[str] = set()


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
    with _LOCK:
        cached = _ZSC_PIPELINE_CACHE.get(model_name)
        if cached is not None:
            return cached
        if model_name in _ZSC_PIPELINE_FAILED:
            return None

    try:
        from transformers import pipeline
    except ImportError:
        logger.info("Transformers is not installed; skipping zero-shot pipeline")
        with _LOCK:
            _ZSC_PIPELINE_FAILED.add(model_name)
        return None

    try:
        local_only = _local_files_only()
        classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            local_files_only=local_only,
        )
        with _LOCK:
            _ZSC_PIPELINE_CACHE[model_name] = classifier
        return classifier
    except Exception:
        logger.exception("Failed to initialize zero-shot pipeline: %s", model_name)
        with _LOCK:
            _ZSC_PIPELINE_FAILED.add(model_name)
        return None
