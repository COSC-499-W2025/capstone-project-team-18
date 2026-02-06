import hashlib
import json
import os
from time import perf_counter
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_MODEL = None
_TOKENIZER = None
_MODEL_FAILED = False
_ML_DISABLED_FOR_RUN = False
_CACHE: dict[str, str] = {}


def _ml_required() -> bool:
    """Return whether callers require ML-only project summaries."""
    return os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML") == "1"


def _fast_mode_enabled() -> bool:
    """Return whether fast generation mode is active (default on)."""
    return os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_FAST_MODE", "1") != "0"


def _env_int(name: str, default: int) -> int:
    """Read an integer env var with safe fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float env var with safe fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return max(0.1, float(raw))
    except (TypeError, ValueError):
        return default


def _max_new_tokens() -> int:
    """Return capped generation length tuned for interactive CLI speed."""
    default = 72 if _fast_mode_enabled() else 120
    return _env_int("ARTIFACT_MINER_PROJECT_SUMMARY_MAX_NEW_TOKENS", default)


def _max_generation_seconds() -> float:
    """Return per-generation timeout in seconds."""
    default = 8.0 if _fast_mode_enabled() else 25.0
    return _env_float("ARTIFACT_MINER_PROJECT_SUMMARY_MAX_TIME_SEC", default)


def _strict_retry_enabled() -> bool:
    """Control whether a strict second pass should run after rejection."""
    override = os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_STRICT_RETRY")
    if override is not None:
        return override == "1"
    return not _fast_mode_enabled()


def _disable_ml_if_slow(elapsed_seconds: float):
    """
    Disable ML summaries for the remainder of the current process if generation
    is consistently too slow. This prevents multi-project CLI runs from appearing
    stalled.
    """
    global _ML_DISABLED_FOR_RUN
    if os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_DISABLE_AFTER_SLOW", "1") == "0":
        return
    threshold = _env_float("ARTIFACT_MINER_PROJECT_SUMMARY_SLOW_THRESHOLD_SEC", 30.0)
    if elapsed_seconds > threshold:
        _ML_DISABLED_FOR_RUN = True
        logger.warning(
            "Project summary generation took %.1fs (> %.1fs); disabling ML summaries for this run",
            elapsed_seconds,
            threshold,
        )


def _get_model_name() -> str:
    """Select model from env override or sensible local default."""
    override = os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_MODEL")
    if override:
        return override

    if torch.cuda.is_available():
        return "microsoft/Phi-3-mini-4k-instruct"
    return "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def _load_model():
    """Load model/tokenizer once and cache globally."""
    global _MODEL, _TOKENIZER, _MODEL_FAILED, _ML_DISABLED_FOR_RUN

    if not ml_extraction_allowed():
        return None, None

    if os.environ.get("ARTIFACT_MINER_DISABLE_PROJECT_SUMMARY_MODEL") == "1":
        logger.info("Project summary model disabled via env variable")
        return None, None

    if _ML_DISABLED_FOR_RUN:
        logger.warning("Project summary skipped: ML disabled for current run due to prior slow generation")
        return None, None

    if _MODEL_FAILED:
        return None, None

    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER

    try:
        load_start = perf_counter()
        model_name = _get_model_name()
        logger.info("Loading project summary model: %s", model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        use_cuda = torch.cuda.is_available()
        dtype = torch.float16 if use_cuda else torch.float32
        device_map = "auto" if use_cuda else "cpu"
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map=device_map,
            low_cpu_mem_usage=True,
        )
        _MODEL = model
        _TOKENIZER = tokenizer
        load_seconds = perf_counter() - load_start
        logger.info("Project summary model loaded in %.1fs", load_seconds)
        return _MODEL, _TOKENIZER
    except Exception:
        logger.exception("Failed to load project summary model")
        _MODEL_FAILED = True
        return None, None


def _facts_hash(facts: dict[str, Any]) -> str:
    """Create stable hash for summary cache."""
    serialized = json.dumps(facts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _build_prompt(facts: dict[str, Any], strict: bool = False) -> str:
    """
    Build strict prompt for grounded project summaries.

    Output must remain 2-3 sentences and reuse only factual terms from the
    payload, with explicit mention of goals, stack, and contribution.
    """
    facts_json = json.dumps(facts, ensure_ascii=True)
    base = (
        "Write a professional 2-3 sentence project summary using ONLY the facts below. "
        "Sentence 1: project goals. Sentence 2: frameworks/languages used. "
        "Sentence 3: contribution details. Do not invent tools, percentages, or roles. "
        "Do not use bullet points."
    )
    if strict:
        must = facts.get("goal_terms", [])[:1] + facts.get("frameworks", [])[:1] + facts.get("languages", [])[:1]
        must_text = ", ".join([str(x) for x in must if x])
        if must_text:
            base += f" You MUST mention at least one of these terms verbatim: {must_text}."
    return f"{base}\n\nFacts (JSON): {facts_json}\n\nSummary:"


def _normalize_summary(text: str) -> str:
    """Normalize model output artifacts to plain summary text."""
    cleaned = text.strip()
    if "Summary:" in cleaned:
        cleaned = cleaned.split("Summary:", 1)[-1].strip()
    return " ".join(cleaned.split())


def _is_list_like(text: str) -> bool:
    """Detect list-like formatting that violates narrative requirement."""
    return "\n-" in text or "\n•" in text


def _summary_mentions_any(summary: str, items: list[str]) -> bool:
    """Return True if summary contains any anchor term."""
    lowered = summary.lower()
    norm_summary = "".join(ch for ch in lowered if ch.isalnum())
    for item in items:
        if not item:
            continue
        item_text = str(item).lower()
        if item_text in lowered:
            return True
        norm_item = "".join(ch for ch in item_text if ch.isalnum())
        if norm_item and norm_item in norm_summary:
            return True
    return False


def _is_valid_summary(summary: str, facts: dict[str, Any]) -> tuple[bool, str]:
    """Validate shape and grounding of generated summary."""
    if _is_list_like(summary):
        return False, "list_like"

    word_count = len(summary.split())
    if word_count < 20 or word_count > 130:
        return False, f"word_count={word_count}"

    sentence_count = summary.count(".")
    if not (2 <= sentence_count <= 3):
        return False, f"sentence_count={sentence_count}"

    goal_terms = facts.get("goal_terms", [])
    stack_terms = facts.get("frameworks", []) + facts.get("languages", [])
    contribution_terms = []
    if facts.get("role"):
        contribution_terms.append(str(facts["role"]))
    if facts.get("commit_focus"):
        contribution_terms.append(str(facts["commit_focus"]))
    if isinstance(facts.get("commit_pct"), (int, float)):
        contribution_terms.append(str(int(round(float(facts["commit_pct"])))))
    if isinstance(facts.get("line_pct"), (int, float)):
        contribution_terms.append(str(int(round(float(facts["line_pct"])))))
    contribution_terms.extend([k for k, _ in facts.get("activity_breakdown", [])[:2]])
    if facts.get("role_description"):
        contribution_terms.extend(str(facts["role_description"]).split()[:3])

    if goal_terms and not _summary_mentions_any(summary, goal_terms):
        return False, "missing_goal_anchor"
    if stack_terms and not _summary_mentions_any(summary, stack_terms):
        return False, "missing_stack_anchor"
    if contribution_terms and not _summary_mentions_any(summary, contribution_terms):
        return False, "missing_contribution_anchor"
    return True, "ok"


def generate_project_summary(facts: dict[str, Any]) -> str | None:
    """
    Generate ML project summary from structured facts.

    Returns None if unavailable/invalid so caller can fallback to deterministic
    summary generation.
    """
    if not facts:
        return None

    cache_key = _facts_hash(facts)
    if cache_key in _CACHE:
        logger.info("Project summary cache hit")
        return _CACHE[cache_key]

    model, tokenizer = _load_model()
    if model is None or tokenizer is None:
        logger.warning("Project summary skipped: model not available")
        return None if _ml_required() else None

    try:
        gen_kwargs = {
            "max_new_tokens": _max_new_tokens(),
            "max_time": _max_generation_seconds(),
            "do_sample": False,
            "temperature": 0.0,
            "top_p": 1.0,
            "pad_token_id": tokenizer.eos_token_id,
        }
        reason = "unknown"
        prompt = _build_prompt(facts, strict=False)
        inputs = tokenizer(prompt, return_tensors="pt")
        pass_start = perf_counter()
        output = model.generate(
            **inputs,
            **gen_kwargs,
        )
        _disable_ml_if_slow(perf_counter() - pass_start)
        summary = _normalize_summary(tokenizer.decode(output[0], skip_special_tokens=True))
        if summary:
            ok, reason = _is_valid_summary(summary, facts)
            if ok:
                _CACHE[cache_key] = summary
                logger.info("Project summary generated successfully")
                return summary
            logger.warning("Project summary rejected (%s): %s", reason, summary[:200])

        if _strict_retry_enabled():
            strict_prompt = _build_prompt(facts, strict=True)
            inputs = tokenizer(strict_prompt, return_tensors="pt")
            pass_start = perf_counter()
            output = model.generate(
                **inputs,
                **gen_kwargs,
            )
            _disable_ml_if_slow(perf_counter() - pass_start)
            summary = _normalize_summary(tokenizer.decode(output[0], skip_special_tokens=True))
            if summary:
                ok, reason = _is_valid_summary(summary, facts)
                if ok:
                    _CACHE[cache_key] = summary
                    logger.info("Project summary generated successfully (strict pass)")
                    return summary
                logger.warning("Project summary rejected after strict pass (%s): %s", reason, summary[:200])
        return None
    except Exception:
        logger.exception("Project summary generation failed")
        return None


def build_project_summary_facts(
    project_name: str | None,
    goal_terms: list[str],
    frameworks: list[str],
    languages: list[str],
    role: str | None,
    commit_focus: str | None,
    commit_pct: float | None,
    line_pct: float | None,
    activity_breakdown: list[tuple[str, float]] | None = None,
    role_description: str | None = None,
) -> dict[str, Any]:
    """Build compact facts payload for ML summary generation."""
    return {
        "project_name": project_name,
        "goal_terms": goal_terms[:4],
        "frameworks": frameworks[:4],
        "languages": languages[:3],
        "role": role,
        "role_description": role_description,
        "commit_focus": commit_focus,
        "commit_pct": commit_pct,
        "line_pct": line_pct,
        "activity_breakdown": activity_breakdown[:3] if activity_breakdown else [],
    }
