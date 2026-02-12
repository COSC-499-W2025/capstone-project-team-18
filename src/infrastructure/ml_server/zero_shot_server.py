"""
Lightweight HTTP service for zero-shot classification used by CLI runtime.

This lets the CLI container avoid loading large transformer models directly.
"""

from __future__ import annotations

import os
import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Artifact Miner ML Server", version="1.0")

_LOCK = threading.Lock()
_PIPELINE_CACHE: dict[str, Any] = {}
_PIPELINE_FAILED: set[str] = set()


def _local_files_only() -> bool:
    return (
        os.environ.get("ARTIFACT_MINER_LOCAL_FILES_ONLY") == "1"
        or os.environ.get("HF_HUB_OFFLINE") == "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )


def _default_model() -> str:
    return os.environ.get("ARTIFACT_MINER_ZSC_MODEL", "facebook/bart-large-mnli")


def _preload_enabled() -> bool:
    return str(os.environ.get("ARTIFACT_MINER_ZSC_PRELOAD", "1")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _load_pipeline(model_name: str):
    with _LOCK:
        cached = _PIPELINE_CACHE.get(model_name)
        if cached is not None:
            return cached
        if model_name in _PIPELINE_FAILED:
            return None

    try:
        from transformers import pipeline
    except Exception as exc:
        raise RuntimeError("transformers_not_available") from exc

    try:
        classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            local_files_only=_local_files_only(),
        )
        with _LOCK:
            _PIPELINE_CACHE[model_name] = classifier
        return classifier
    except Exception:
        with _LOCK:
            _PIPELINE_FAILED.add(model_name)
        return None


class ZeroShotRequest(BaseModel):
    model: str = Field(default_factory=_default_model)
    inputs: str | list[str]
    candidate_labels: list[str]
    multi_label: bool = False
    batch_size: int = 16
    hypothesis_template: str | None = None


@app.on_event("startup")
def preload_default_model() -> None:
    if not _preload_enabled():
        return
    _load_pipeline(_default_model())


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/v1/models")
def models() -> dict[str, list[str]]:
    with _LOCK:
        loaded = sorted(_PIPELINE_CACHE.keys())
    return {"loaded_models": loaded}


@app.post("/v1/zero-shot/classify")
def classify_zero_shot(payload: ZeroShotRequest) -> dict[str, list[dict[str, Any]]]:
    labels = [str(label).strip() for label in payload.candidate_labels if str(label).strip()]
    if not labels:
        raise HTTPException(status_code=400, detail="candidate_labels must not be empty")

    if isinstance(payload.inputs, str):
        sequences = [payload.inputs]
    else:
        sequences = [str(item) for item in payload.inputs]
    if not sequences:
        return {"results": []}

    classifier = _load_pipeline(payload.model)
    if classifier is None:
        raise HTTPException(status_code=503, detail=f"model_unavailable:{payload.model}")

    kwargs: dict[str, Any] = {
        "multi_label": bool(payload.multi_label),
        "batch_size": max(1, int(payload.batch_size)),
    }
    if payload.hypothesis_template:
        kwargs["hypothesis_template"] = payload.hypothesis_template

    try:
        raw = classifier(sequences, labels, **kwargs)
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            raise RuntimeError("invalid_result_shape")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"classification_failed:{exc}") from exc

    if len(raw) != len(sequences):
        raise HTTPException(status_code=500, detail="classification_count_mismatch")

    results: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise HTTPException(status_code=500, detail="malformed_result_item")
        labels_out = item.get("labels")
        scores_out = item.get("scores")
        if not isinstance(labels_out, list) or not isinstance(scores_out, list):
            raise HTTPException(status_code=500, detail="missing_labels_or_scores")
        if len(labels_out) != len(scores_out):
            raise HTTPException(status_code=500, detail="labels_scores_length_mismatch")

        try:
            normalized_scores = [float(score) for score in scores_out]
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=500, detail="non_numeric_scores") from exc

        results.append({
            "labels": [str(label) for label in labels_out],
            "scores": normalized_scores,
        })

    return {"results": results}
