import hashlib
import json
import os
import re
from time import perf_counter
from typing import Any

from src.core.ML.models.model_runtime import cuda_available, get_causal_lm
from src.core.ML.models.llama_cpp_runtime import (
    llama_cpp_enabled,
    resolve_llama_cpp_model_path,
    llama_cpp_generate_json_object,
    llama_cpp_generate_text,
)
from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_MODEL = None
_TOKENIZER = None
_MODEL_FAILED = False
_ML_DISABLED_FOR_RUN = False
_CACHE: dict[str, str] = {}
_LLAMA_CPP_TOTAL_SECONDS = 0.0
_LLAMA_CPP_RUN_BUDGET_OVERRIDE_SECONDS: float | None = None
_LLAMA_CPP_PER_PROJECT_MAX_OVERRIDE_SECONDS: float | None = None


def _ml_required() -> bool:
    """Return whether callers require ML-only project summaries."""
    return os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML") == "1"


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp numeric values to a closed interval."""
    return max(lower, min(upper, value))


def configure_project_summary_run(project_count: int):
    """
    Configure dynamic llama-cpp timing budgets for the current portfolio run.

    This function is intended to be called once before iterating project
    summaries. It resets per-run counters and computes dynamic budget values
    from project_count unless explicitly disabled.
    """
    global _ML_DISABLED_FOR_RUN
    global _LLAMA_CPP_TOTAL_SECONDS
    global _LLAMA_CPP_RUN_BUDGET_OVERRIDE_SECONDS
    global _LLAMA_CPP_PER_PROJECT_MAX_OVERRIDE_SECONDS

    _ML_DISABLED_FOR_RUN = False
    _LLAMA_CPP_TOTAL_SECONDS = 0.0
    _LLAMA_CPP_RUN_BUDGET_OVERRIDE_SECONDS = None
    _LLAMA_CPP_PER_PROJECT_MAX_OVERRIDE_SECONDS = None

    if os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_DYNAMIC_BUDGET", "1") == "0":
        logger.info("Project summary dynamic budget disabled via env variable")
        return

    if project_count <= 0:
        return

    try:
        count = max(1, int(project_count))
    except (TypeError, ValueError):
        count = 1

    explicit_run_budget = bool(os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_RUN_BUDGET_SEC"))
    explicit_per_project = bool(os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_MAX_SEC"))
    if explicit_run_budget:
        logger.info("Project summary dynamic run budget skipped due to explicit run budget env")
    if explicit_per_project:
        logger.info("Project summary dynamic per-project timeout skipped due to explicit max-sec env")

    fast_mode = _fast_mode_enabled()
    target_total = _env_float(
        "ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_TARGET_TOTAL_SEC",
        300.0 if fast_mode else 480.0,
    )
    warmup = _env_float(
        "ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_WARMUP_SEC",
        25.0 if fast_mode else 40.0,
    )
    min_per_project = _env_float(
        "ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_MIN_PER_PROJECT_SEC",
        10.0 if fast_mode else 14.0,
    )
    max_per_project = _env_float(
        "ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_MAX_PER_PROJECT_SEC",
        35.0 if fast_mode else 60.0,
    )
    if max_per_project < min_per_project:
        max_per_project = min_per_project

    distributable = max(min_per_project, target_total - warmup)
    per_project = _clamp(distributable / float(count), min_per_project, max_per_project)
    raw_run_budget = warmup + (per_project * float(count))
    run_budget = max(30.0, min(target_total, raw_run_budget))

    if not explicit_per_project:
        _LLAMA_CPP_PER_PROJECT_MAX_OVERRIDE_SECONDS = per_project
    if not explicit_run_budget:
        _LLAMA_CPP_RUN_BUDGET_OVERRIDE_SECONDS = run_budget

    logger.info(
        (
            "Configured dynamic project-summary llama budget: projects=%d, "
            "per_project=%.1fs, run_budget=%.1fs (target_total=%.1fs, warmup=%.1fs, explicit_run_budget=%s, explicit_per_project=%s)"
        ),
        count,
        per_project,
        run_budget,
        target_total,
        warmup,
        explicit_run_budget,
        explicit_per_project,
    )


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


def _llama_cpp_max_tokens() -> int:
    """
    Keep project-summary generation tightly bounded for CLI responsiveness.
    """
    default = 72 if _fast_mode_enabled() else 120
    return max(48, min(160, _env_int("ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_MAX_TOKENS", default)))


def _llama_cpp_max_retries() -> int:
    """
    Default to one attempt in fast mode; fallback/repair handles malformed text.
    """
    default = 0 if _fast_mode_enabled() else 1
    return max(0, min(2, _env_int("ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_MAX_RETRIES", default)))


def _llama_cpp_max_total_seconds() -> float:
    """Per-project upper budget for llama-cpp generation attempts."""
    if _LLAMA_CPP_PER_PROJECT_MAX_OVERRIDE_SECONDS is not None:
        return _LLAMA_CPP_PER_PROJECT_MAX_OVERRIDE_SECONDS
    default = 30.0 if _fast_mode_enabled() else 70.0
    return max(8.0, _env_float("ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_MAX_SEC", default))


def _llama_cpp_run_budget_seconds() -> float:
    """Total run-time budget for llama-cpp project summaries across a CLI run."""
    if _LLAMA_CPP_RUN_BUDGET_OVERRIDE_SECONDS is not None:
        return _LLAMA_CPP_RUN_BUDGET_OVERRIDE_SECONDS
    default = 120.0 if _fast_mode_enabled() else 240.0
    return max(30.0, _env_float("ARTIFACT_MINER_PROJECT_SUMMARY_LLAMA_RUN_BUDGET_SEC", default))


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


def _disable_llama_cpp_if_over_budget(elapsed_seconds: float):
    """
    Disable llama-cpp project summaries once cumulative time exceeds budget.
    """
    global _ML_DISABLED_FOR_RUN, _LLAMA_CPP_TOTAL_SECONDS
    _LLAMA_CPP_TOTAL_SECONDS += max(0.0, float(elapsed_seconds))
    budget = _llama_cpp_run_budget_seconds()
    if _LLAMA_CPP_TOTAL_SECONDS > budget:
        _ML_DISABLED_FOR_RUN = True
        logger.warning(
            "llama-cpp project summaries exceeded run budget (%.1fs > %.1fs); using deterministic fallback for remaining projects",
            _LLAMA_CPP_TOTAL_SECONDS,
            budget,
        )


def _get_model_name() -> str:
    """Select model from env override or sensible local default."""
    override = os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_MODEL")
    if override:
        return override

    if cuda_available():
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
        model, tokenizer = get_causal_lm(model_name)
        if model is None or tokenizer is None:
            _MODEL_FAILED = True
            return None, None
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


def _cache_enabled() -> bool:
    """Allow disabling cache for strict per-run ML generation checks."""
    return os.environ.get("ARTIFACT_MINER_SUMMARY_CACHE_DISABLE", "0") != "1"


def _llama_cpp_model_path() -> str | None:
    """Resolve GGUF model path for project summary generation."""
    return resolve_llama_cpp_model_path("ARTIFACT_MINER_LLAMA_CPP_PROJECT_MODEL_PATH")


def _build_llama_cpp_prompt(facts: dict[str, Any]) -> str:
    """
    Build strict structured prompt for llama-cpp project summary generation.
    """
    facts_json = json.dumps(facts, ensure_ascii=True)
    return (
        "TASK: PROJECT_SUMMARY\n"
        "Return exactly one JSON object with this schema:\n"
        '{"summary":"string"}\n'
        "Hard constraints:\n"
        "- 2 to 3 sentences.\n"
        "- 20 to 130 words.\n"
        "- Cover goals, stack, and contribution.\n"
        "- Use only facts from the payload.\n"
        "- Do not invent tools, roles, percentages, or outcomes.\n"
        "- Do not include any key besides summary.\n"
        "- Output must be valid JSON and nothing else.\n\n"
        f"FACTS_JSON: {facts_json}"
    )


def _build_llama_cpp_plain_prompt(facts: dict[str, Any]) -> str:
    """
    Build a plain-text prompt used to recover from malformed JSON responses.
    """
    facts_json = json.dumps(facts, ensure_ascii=True)
    return (
        "Write a professional project summary in exactly 2 to 3 sentences.\n"
        "Constraints:\n"
        "- 20 to 130 words.\n"
        "- Cover goals, stack, and contribution.\n"
        "- Use only the facts provided.\n"
        "- No bullet points.\n"
        "- Return only the summary text.\n\n"
        f"FACTS_JSON: {facts_json}\n\n"
        "Summary:"
    )


def _build_llama_cpp_structural_retry_prompt(facts: dict[str, Any], draft_summary: str, rejection_reason: str) -> str:
    """
    Build a rewrite prompt for structurally invalid summaries (too short/one sentence).
    """
    facts_json = json.dumps(facts, ensure_ascii=True)
    return (
        "TASK: PROJECT_SUMMARY_REWRITE\n"
        "Rewrite DRAFT_SUMMARY into a professional 2 to 3 sentence project summary.\n"
        "Hard constraints:\n"
        "- 20 to 130 words.\n"
        "- Keep only information grounded in FACTS_JSON and DRAFT_SUMMARY.\n"
        "- Cover goals, stack, and contribution.\n"
        "- Do not invent tools, percentages, roles, or outcomes.\n"
        "- No bullet points.\n"
        "- Return only the rewritten summary text.\n\n"
        f"REJECTION_REASON: {rejection_reason}\n\n"
        f"FACTS_JSON: {facts_json}\n\n"
        f"DRAFT_SUMMARY: {draft_summary}\n\n"
        "Rewritten summary:"
    )


def _extract_summary_from_payload(payload: Any) -> str | None:
    """
    Extract summary text from tolerant payload shapes.
    """
    if not isinstance(payload, dict):
        return None

    direct = payload.get("summary")
    if isinstance(direct, str):
        return direct

    for key in ("project_summary", "result", "response", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = _extract_summary_from_payload(value)
            if nested:
                return nested

    for value in payload.values():
        if isinstance(value, str) and len(value.split()) >= 5:
            return value
        if isinstance(value, dict):
            nested = _extract_summary_from_payload(value)
            if nested:
                return nested
    return None


def _strip_markdown_fence(text: str) -> str:
    """
    Remove single code-fence wrappers around model output.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) < 3:
        return stripped
    if not lines[0].startswith("```") or lines[-1].strip() != "```":
        return stripped
    return "\n".join(lines[1:-1]).strip()


def _extract_summary_from_raw_text(raw_text: str) -> str | None:
    """
    Recover summary text when llama-cpp output is not valid JSON.
    """
    if not raw_text:
        return None

    cleaned = _strip_markdown_fence(raw_text)

    # Sometimes the model still returns JSON-ish text in plain mode.
    try:
        payload = json.loads(cleaned)
        summary = _extract_summary_from_payload(payload)
        if summary:
            return summary
    except Exception:
        pass

    return cleaned


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
    # Fix tokenization artifacts in percentages (e.g., "42. 86%" -> "42.86%").
    cleaned = re.sub(r"\b(\d{1,3})\.\s+(\d{1,3})\s*%", r"\1.\2%", cleaned)
    cleaned = re.sub(r"\b(\d{1,3})\s+%", r"\1%", cleaned)
    return " ".join(cleaned.split())


def _align_summary_percentages(summary: str, facts: dict[str, Any]) -> str:
    """
    Align percentage mentions in summary text with canonical fact values.

    This preserves model wording but ensures displayed percentages are consistent
    with stats used elsewhere (e.g., resume section).
    """
    if not summary:
        return summary

    updated = summary

    commit_pct = _normalize_percentage(facts.get("commit_pct"))
    if isinstance(commit_pct, (int, float)):
        commit_str = f"{int(round(float(commit_pct)))}%"
        updated = re.sub(
            r"(?i)(\bcommits?\b[^.?!%]{0,20}?)(\d{1,3}(?:\.\d+)?)\s*%",
            lambda m: f"{m.group(1)}{commit_str}",
            updated,
        )
        updated = re.sub(
            r"(?i)(\d{1,3}(?:\.\d+)?)\s*%\s*(?:of\s+)?(commits?\b)",
            lambda m: f"{commit_str} {m.group(2)}",
            updated,
        )
        updated = re.sub(
            r"(?i)(\bcommits?\b\s*[:\-]?\s*)(\d{1,3}(?:\.\d+)?)\s*%",
            lambda m: f"{m.group(1)}{commit_str}",
            updated,
        )

    line_pct = _normalize_percentage(facts.get("line_pct"))
    if isinstance(line_pct, (int, float)):
        line_str = f"{int(round(float(line_pct)))}%"
        updated = re.sub(
            r"(?i)(\blines?\b[^.?!%]{0,20}?)(\d{1,3}(?:\.\d+)?)\s*%",
            lambda m: f"{m.group(1)}{line_str}",
            updated,
        )
        updated = re.sub(
            r"(?i)(\d{1,3}(?:\.\d+)?)\s*%\s*(?:of\s+)?(lines?\b)",
            lambda m: f"{line_str} {m.group(2)}",
            updated,
        )
        updated = re.sub(
            r"(?i)(\blines?\b\s*[:\-]?\s*)(\d{1,3}(?:\.\d+)?)\s*%",
            lambda m: f"{m.group(1)}{line_str}",
            updated,
        )

    def _domain_aliases(domain_text: str) -> list[str]:
        base = domain_text.strip().lower()
        aliases = {base}
        if base.endswith("e"):
            aliases.add(base[:-1] + "ing")
        else:
            aliases.add(base + "ing")
        if base == "code":
            # Keep aliases specific to contribution activity; avoid broad
            # nouns like "development" that can appear in general prose.
            aliases.update({"coding"})
        if base == "test":
            aliases.update({"testing", "tests", "qa"})
        if base == "documentation":
            aliases.update({"docs", "documenting"})
        # Prefer exact/base activity terms before variants.
        ordered = [base]
        for alias in sorted(aliases):
            if alias != base:
                ordered.append(alias)
        return ordered

    for domain, pct in facts.get("activity_breakdown", []):
        domain_text = str(domain or "").strip().lower()
        if not domain_text:
            continue
        pct_str = f"{int(round(float(pct)))}%"

        # Normalize mentions like "coding (42.86%)" / "testing activities" to include
        # the canonical percentage from facts while preserving surrounding ML phrasing.
        replaced = False
        for alias in _domain_aliases(domain_text):
            alias_pattern = re.escape(alias)
            qualifier_pattern = r"(?:development|work|changes?|activities?|tasks?)"

            def _replace_phrase_percent(match: re.Match[str]) -> str:
                nonlocal replaced
                phrase = match.group(1)
                replaced = True
                return f"{phrase} ({pct_str})"

            # Replace existing percentages bound to an activity phrase
            # (e.g., "code development (27%)", "testing activities (20%)").
            updated, phrase_count = re.subn(
                rf"(?i)\b({alias_pattern}(?:\s+{qualifier_pattern})?)\b\s*\(\s*\d{{1,3}}(?:\.\d+)?%\s*\)",
                _replace_phrase_percent,
                updated,
                count=1,
            )
            if phrase_count > 0:
                break

            def _attach_or_replace(match: re.Match[str]) -> str:
                nonlocal replaced
                token = match.group(1)
                replaced = True
                return f"{token} ({pct_str})"

            updated, count = re.subn(
                rf"(?i)\b({alias_pattern})\b(?:\s*\(\s*\d{{1,3}}(?:\.\d+)?%\s*\))?",
                _attach_or_replace,
                updated,
                count=1,
            )
            if count > 0:
                break

    return updated


def _dedupe_percentage_mentions(summary: str, facts: dict[str, Any]) -> str:
    """
    Remove redundant repeated percentage annotations for the same metric.

    Keeps the first percentage mention for each canonical metric/activity and
    strips later duplicate parenthetical percentages to avoid noisy repetition.
    """
    if not summary:
        return summary

    updated = summary
    seen: set[str] = set()

    def _domain_aliases(domain_text: str) -> list[str]:
        base = domain_text.strip().lower()
        aliases = {base}
        if base.endswith("e"):
            aliases.add(base[:-1] + "ing")
        else:
            aliases.add(base + "ing")
        if base == "code":
            aliases.update({"coding"})
        if base == "test":
            aliases.update({"testing", "tests", "qa"})
        if base == "documentation":
            aliases.update({"docs", "documenting"})
        ordered = [base]
        for alias in sorted(aliases):
            if alias != base:
                ordered.append(alias)
        return ordered

    # Activity metrics
    for domain, _pct in facts.get("activity_breakdown", []):
        canonical = str(domain or "").strip().lower()
        if not canonical:
            continue
        qualifier_pattern = r"(?:development|work|changes?|activities?|tasks?)"
        for alias in _domain_aliases(canonical):
            alias_pattern = re.escape(alias)

            def _dedupe_activity(match: re.Match[str]) -> str:
                phrase = match.group(1)
                pct = match.group(2)
                key = f"activity:{canonical}"
                if key in seen:
                    return phrase
                seen.add(key)
                return f"{phrase} ({pct}%)"

            updated = re.sub(
                rf"(?i)\b({alias_pattern}(?:\s+{qualifier_pattern})?)\b\s*\(\s*(\d{{1,3}}(?:\.\d+)?)%\s*\)",
                _dedupe_activity,
                updated,
            )

    # Commits metric
    def _dedupe_commits_forward(match: re.Match[str]) -> str:
        pct = match.group(1)
        metric = match.group(2)
        key = "metric:commits"
        if key in seen:
            return metric
        seen.add(key)
        return f"{pct}% {metric}"

    updated = re.sub(
        r"(?i)(\d{1,3}(?:\.\d+)?)\s*%\s*(?:of\s+)?(commits?\b)",
        _dedupe_commits_forward,
        updated,
    )

    def _dedupe_lines_forward(match: re.Match[str]) -> str:
        pct = match.group(1)
        metric = match.group(2)
        key = "metric:lines"
        if key in seen:
            return metric
        seen.add(key)
        return f"{pct}% {metric}"

    updated = re.sub(
        r"(?i)(\d{1,3}(?:\.\d+)?)\s*%\s*(?:of\s+)?(lines?\b)",
        _dedupe_lines_forward,
        updated,
    )

    return updated


def _normalize_contribution_percentage_noise(summary: str, facts: dict[str, Any]) -> str:
    """
    Remove conflicting/duplicate generic contribution percentages when activity
    percentages are already grounded in the sentence.
    """
    if not summary:
        return summary

    updated = summary
    activity = [(str(k).strip().lower(), float(v)) for k, v in facts.get("activity_breakdown", []) if str(k).strip()]
    if not activity:
        return updated

    # Normalize common noisy constructions while preserving activity percentages.
    updated = re.sub(
        r"(?i)\bcontributed\s+\d{1,3}%\s+of\s+(?:their\s+)?(?:contributions?|efforts?|work)\s+",
        "contributed through ",
        updated,
    )
    updated = re.sub(
        r"(?i)\bwith\s+\d{1,3}%\s+of\s+(?:their\s+)?(?:contributions?|efforts?|work)\s+",
        "with ",
        updated,
    )
    updated = re.sub(
        r"(?i)\b\d{1,3}%\s+of\s+(?:their\s+)?(?:contributions?|efforts?|work)\b",
        "",
        updated,
    )

    # Remove duplicated "remaining X%" when activity phrase already has "(X%)".
    updated = re.sub(
        r"(?i)\bthe\s+remaining\s+\d{1,3}%\s+in\s+((?:code|coding|test|testing|documentation|docs)\s*\(\s*\d{1,3}%\s*\))",
        r"\1",
        updated,
    )

    updated = re.sub(r"\s{2,}", " ", updated).strip()
    updated = re.sub(r"\s+,", ",", updated)
    return updated


def _is_list_like(text: str) -> bool:
    """Detect list-like formatting that violates narrative requirement."""
    return "\n-" in text or "\n•" in text


def _sentence_count(text: str) -> int:
    """
    Count sentence-like segments using punctuation boundaries.

    This treats `.`, `!`, and `?` as sentence endings and avoids relying on a
    raw period count.
    """
    parts = _sentence_segments(text)
    return len(parts)


def _sentence_segments(text: str) -> list[str]:
    """
    Split text into sentence-like segments without breaking decimal numbers.

    A period between digits (e.g., 42.86) is treated as numeric punctuation,
    not a sentence boundary.
    """
    if not text:
        return []
    # Split on punctuation only when the delimiter is not part of a decimal.
    raw_parts = re.split(r"(?:(?<!\d)\.|\.(?!\d)|[!?])+", text)
    return [segment.strip() for segment in raw_parts if segment and segment.strip()]


def _has_dangling_numeric_fragment(summary: str) -> bool:
    """
    Detect truncated numeric fragments (e.g., '(39.') from clipped model output.
    """
    stripped = summary.strip()
    return bool(re.search(r"\(\d{1,3}\.\s*$", stripped))


def _summary_mentions_any(summary: str, items: list[str]) -> bool:
    """Return True if summary contains any anchor term."""
    lowered = summary.lower()
    norm_summary = "".join(ch for ch in lowered if ch.isalnum())
    summary_tokens = set(_normalized_tokens(summary))
    for item in items:
        if not item:
            continue
        item_text = str(item).lower()
        if item_text in lowered:
            return True
        norm_item = "".join(ch for ch in item_text if ch.isalnum())
        if norm_item and norm_item in norm_summary:
            return True
        item_tokens = [tok for tok in _normalized_tokens(item_text) if tok]
        if item_tokens and all(tok in summary_tokens for tok in item_tokens):
            return True
    return False


def _normalize_percentage(value: float | int | None) -> float | None:
    """
    Normalize a ratio/percentage input into a percentage value.

    Expected canonical range is 0-100. Values in [0, 1] are treated as ratios
    and converted to percentages. This prevents mixed-unit bugs at render time.
    """
    if not isinstance(value, (int, float)):
        return None
    pct = float(value)
    if 0.0 <= pct <= 1.0:
        pct *= 100.0
    return pct


def _normalized_token(token: str) -> str:
    """Normalize a token with simple plural handling for robust anchor matching."""
    cleaned = "".join(ch for ch in token.lower() if ch.isalnum())
    if not cleaned:
        return ""
    if cleaned.endswith("ies") and len(cleaned) > 4:
        return cleaned[:-3] + "y"
    if cleaned.endswith("es") and len(cleaned) > 4:
        return cleaned[:-2]
    if cleaned.endswith("s") and len(cleaned) > 3:
        return cleaned[:-1]
    return cleaned


def _normalized_tokens(text: str) -> list[str]:
    """Tokenize and normalize a text blob for forgiving containment checks."""
    raw = re.findall(r"[a-zA-Z0-9]+", str(text).lower())
    normalized: list[str] = []
    for tok in raw:
        cleaned = _normalized_token(tok)
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _percentage_anchor_terms(value: float | int | None) -> list[str]:
    """Build percentage anchor variants (e.g., '42%', '42 percent', '42')."""
    normalized = _normalize_percentage(value)
    if normalized is None:
        return []
    whole = int(round(float(normalized)))
    return [f"{whole}%", f"{whole} percent", str(whole)]


def _is_valid_summary(summary: str, facts: dict[str, Any]) -> tuple[bool, str]:
    """Validate shape and grounding of generated summary."""
    if _is_list_like(summary):
        return False, "list_like"
    if _has_dangling_numeric_fragment(summary):
        return False, "dangling_numeric_fragment"

    min_words = 18 if _ml_required() else 20
    max_words = 150 if _ml_required() else 130
    word_count = len(summary.split())
    if word_count < min_words or word_count > max_words:
        return False, f"word_count={word_count}"

    max_sentences = 4 if _ml_required() else 3
    sentence_count = _sentence_count(summary)
    if not (2 <= sentence_count <= max_sentences):
        return False, f"sentence_count={sentence_count}"

    goal_terms = facts.get("goal_terms", [])
    stack_terms = facts.get("frameworks", []) + facts.get("languages", [])
    contribution_text_terms = []
    contribution_pct_terms = []
    if facts.get("role"):
        contribution_text_terms.append(str(facts["role"]))
    if facts.get("commit_focus"):
        contribution_text_terms.append(str(facts["commit_focus"]))
    contribution_pct_terms.extend(_percentage_anchor_terms(facts.get("commit_pct")))
    contribution_pct_terms.extend(_percentage_anchor_terms(facts.get("line_pct")))
    contribution_text_terms.extend([k for k, _ in facts.get("activity_breakdown", [])[:2]])
    if facts.get("role_description"):
        contribution_text_terms.extend(str(facts["role_description"]).split()[:3])

    if goal_terms and not _summary_mentions_any(summary, goal_terms):
        return False, "missing_goal_anchor"
    if stack_terms and not _summary_mentions_any(summary, stack_terms):
        return False, "missing_stack_anchor"
    # Contribution can be grounded by textual signals (role/focus/activity) or
    # numeric percentage signals when available.
    has_text_contribution = (
        bool(contribution_text_terms) and _summary_mentions_any(summary, contribution_text_terms)
    )
    has_pct_contribution = (
        bool(contribution_pct_terms) and _summary_mentions_any(summary, contribution_pct_terms)
    )
    if (contribution_text_terms or contribution_pct_terms) and not (has_text_contribution or has_pct_contribution):
        if _ml_required():
            return True, "ok_ml_relaxed_contribution"
        return False, "missing_contribution_anchor"
    return True, "ok"


def _join_english(items: list[str], limit: int = 3) -> str:
    """Join phrase fragments into readable English."""
    trimmed = [str(item).strip() for item in items if str(item).strip()][:limit]
    if not trimmed:
        return ""
    if len(trimmed) == 1:
        return trimmed[0]
    if len(trimmed) == 2:
        return f"{trimmed[0]} and {trimmed[1]}"
    return f"{', '.join(trimmed[:-1])}, and {trimmed[-1]}"


def _grounded_summary_fallback(facts: dict[str, Any]) -> str:
    """
    Build a deterministic 3-sentence summary anchored to project facts.
    """
    goal_terms = [str(x).strip() for x in facts.get("goal_terms", []) if str(x).strip()]
    frameworks = [str(x).strip() for x in facts.get("frameworks", []) if str(x).strip()]
    languages = [str(x).strip() for x in facts.get("languages", []) if str(x).strip()]
    role = str(facts.get("role", "") or "").replace("_", " ").strip()
    commit_focus = str(facts.get("commit_focus", "") or "").replace("_", " ").strip()
    role_description = str(facts.get("role_description", "") or "").strip()
    commit_pct = _normalize_percentage(facts.get("commit_pct"))
    line_pct = _normalize_percentage(facts.get("line_pct"))
    activity = [(str(k).replace("_", " "), float(v)) for k, v in facts.get("activity_breakdown", [])[:2]]

    if goal_terms:
        top_goals = goal_terms[:2]
        if len(top_goals) == 1:
            sentence_1 = f"The project focused on {top_goals[0]} outcomes."
        else:
            sentence_1 = f"The project focused on {top_goals[0]} and {top_goals[1]} outcomes."
    else:
        project_name = str(facts.get("project_name", "") or "").replace("-", " ").replace("_", " ").strip().lower()
        sentence_1 = (
            f"The project focused on {project_name} outcomes."
            if project_name
            else "The project focused on clearly scoped product outcomes."
        )

    if frameworks and languages:
        sentence_2 = (
            f"It was implemented with {_join_english(frameworks[:3])} and primarily written in "
            f"{_join_english(languages[:2])}."
        )
    elif frameworks:
        sentence_2 = f"It was implemented with {_join_english(frameworks[:3])}."
    elif languages:
        sentence_2 = f"It was primarily written in {_join_english(languages[:2])}."
    else:
        sentence_2 = "The implementation stack matched the delivery requirements."

    if role_description:
        sentence_3 = role_description.rstrip(".") + "."
    else:
        contribution_bits: list[str] = []
        if role:
            contribution_bits.append(f"as a {role}")
        if isinstance(commit_pct, (int, float)):
            contribution_bits.append(f"covering about {int(round(commit_pct))}% of commits")
        if isinstance(line_pct, (int, float)):
            contribution_bits.append(f"about {int(round(line_pct))}% of total changed lines")
        if commit_focus:
            contribution_bits.append(f"with emphasis on {commit_focus} work")
        if activity:
            top_activity_terms = [name for name, _ in activity]
            contribution_bits.append(f"across {_join_english(top_activity_terms, limit=2)} changes")
        if contribution_bits:
            sentence_3 = f"I contributed {_join_english(contribution_bits, limit=3)}."
        else:
            sentence_3 = "I contributed through consistent implementation and documentation work."

    return " ".join([sentence_1, sentence_2, sentence_3]).strip()


def _trim_to_max_sentences(summary: str, max_sentences: int = 3) -> str:
    """Trim to sentence cap while preserving terminal punctuation."""
    sentences = _sentence_segments(summary)
    if not sentences:
        return summary
    trimmed = ". ".join(sentences[:max_sentences]).strip()
    if not trimmed.endswith("."):
        trimmed += "."
    return trimmed


def _repair_summary(summary: str | None, facts: dict[str, Any]) -> str:
    """
    Repair malformed ML output so validation failures are rare and predictable.
    """
    normalized = _normalize_summary(summary or "")
    normalized = _align_summary_percentages(normalized, facts)
    normalized = _dedupe_percentage_mentions(normalized, facts)
    normalized = _normalize_contribution_percentage_noise(normalized, facts)
    normalized = _trim_to_max_sentences(
        normalized,
        max_sentences=4 if _ml_required() else 3,
    )

    # In ML-required mode, never splice deterministic template text into output.
    if _ml_required():
        if not normalized:
            logger.info("Project summary rejected in ML-only mode for %s (reason=empty_normalized)", facts.get("project_name"))
        return normalized

    if not normalized:
        return _grounded_summary_fallback(facts)

    ok, reason = _is_valid_summary(normalized, facts)
    if ok:
        return normalized

    fallback = _grounded_summary_fallback(facts)

    # If output is too short/structurally wrong, grounded fallback is safer.
    structural_failure = (
        reason.startswith("word_count=")
        or reason.startswith("sentence_count=")
        or reason in {"list_like"}
    )
    if structural_failure:
        logger.info(
            "Project summary fallback engaged for %s (reason=%s)",
            facts.get("project_name"),
            reason,
        )
        return fallback

    repaired = normalized
    missing_goal = reason == "missing_goal_anchor"
    missing_stack = reason == "missing_stack_anchor"
    missing_contrib = reason == "missing_contribution_anchor"
    if missing_goal or missing_stack or missing_contrib:
        repaired = f"{repaired.rstrip('.')} {fallback}"
        repaired = _normalize_summary(repaired)
        repaired = _trim_to_max_sentences(repaired, max_sentences=3)
        repaired_ok, _ = _is_valid_summary(repaired, facts)
        if repaired_ok:
            return repaired

    fallback_ok, _ = _is_valid_summary(fallback, facts)
    if fallback_ok:
        logger.info(
            "Project summary fallback engaged for %s (reason=%s)",
            facts.get("project_name"),
            reason,
        )
        return fallback
    return normalized


def _validated_fallback_summary(facts: dict[str, Any], *, context: str) -> str | None:
    """
    Build and validate deterministic fallback summary.
    """
    fallback = _repair_summary(_grounded_summary_fallback(facts), facts)
    ok, reason = _is_valid_summary(fallback, facts)
    if ok:
        return fallback
    logger.warning("Project summary fallback rejected%s (%s)", context, reason)
    return None


def _llama_cpp_response_valid(response: dict[str, Any], facts: dict[str, Any]) -> tuple[bool, str]:
    """Validate structured llama-cpp response payload."""
    if not isinstance(response, dict):
        return False, "not_object"

    summary = _extract_summary_from_payload(response)
    if not summary:
        return False, "missing_summary"

    repaired = _repair_summary(summary, facts)
    if not repaired:
        return False, "empty_summary"
    response.clear()
    response["summary"] = repaired
    return _is_valid_summary(repaired, facts)


def _should_retry_structural_with_llama(reason: str) -> bool:
    """Retry with an ML rewrite when failure is likely recoverable via reshaping."""
    if reason in {"list_like", "dangling_numeric_fragment"}:
        return True
    if reason.startswith("sentence_count="):
        return True
    if reason.startswith("word_count="):
        return True
    return False


def _generate_project_summary_with_llama_cpp(facts: dict[str, Any]) -> str | None:
    """
    Generate project summary via local llama-cpp GGUF model.
    """
    if not llama_cpp_enabled():
        return None
    if not ml_extraction_allowed():
        return None
    if _ML_DISABLED_FOR_RUN:
        logger.warning("Project summary skipped: llama-cpp disabled for this run due to prior timeout budget")
        return None
    if os.environ.get("ARTIFACT_MINER_DISABLE_PROJECT_SUMMARY_MODEL") == "1":
        return None

    model_path = _llama_cpp_model_path()
    if not model_path:
        logger.warning("llama-cpp enabled but no project-summary GGUF model path could be resolved")
        return None

    project_name = str(facts.get("project_name") or "unknown-project")
    started_at = perf_counter()
    logger.info("Project summary llama-cpp start for %s", project_name)
    response = llama_cpp_generate_json_object(
        model_path=model_path,
        prompt=_build_llama_cpp_prompt(facts),
        validator=lambda payload: _llama_cpp_response_valid(payload, facts),
        max_retries=_llama_cpp_max_retries(),
        max_tokens=_llama_cpp_max_tokens(),
        temperature=0.0,
        top_p=0.95,
        max_total_seconds=_llama_cpp_max_total_seconds(),
    )
    summary_text = _extract_summary_from_payload(response) if isinstance(response, dict) else None

    # Recover from malformed/non-JSON outputs with one short plain-text pass.
    if not summary_text:
        recovery_max_seconds = max(4.0, min(12.0, _llama_cpp_max_total_seconds() / 2.0))
        raw_text = llama_cpp_generate_text(
            model_path=model_path,
            prompt=_build_llama_cpp_plain_prompt(facts),
            max_retries=0,
            max_tokens=max(48, min(120, _llama_cpp_max_tokens())),
            temperature=0.0,
            top_p=0.95,
            max_total_seconds=recovery_max_seconds,
        )
        summary_text = _extract_summary_from_raw_text(raw_text) if raw_text else None

    elapsed = perf_counter() - started_at
    _disable_llama_cpp_if_over_budget(elapsed)

    if not summary_text:
        logger.warning(
            "llama-cpp project summary failed validation/response for %s (elapsed=%.1fs)",
            project_name,
            elapsed,
        )
        return None

    repaired = _repair_summary(summary_text, facts)
    ok, reason = _is_valid_summary(repaired, facts)
    if not ok and _should_retry_structural_with_llama(reason):
        retry_max_seconds = max(5.0, min(14.0, _llama_cpp_max_total_seconds() / 2.0))
        rewrite_text = llama_cpp_generate_text(
            model_path=model_path,
            prompt=_build_llama_cpp_structural_retry_prompt(facts, summary_text, reason),
            max_retries=0,
            max_tokens=max(56, min(132, _llama_cpp_max_tokens() + 16)),
            temperature=0.0,
            top_p=0.95,
            max_total_seconds=retry_max_seconds,
        )
        rewritten = _extract_summary_from_raw_text(rewrite_text) if rewrite_text else None
        if rewritten:
            repaired_retry = _repair_summary(rewritten, facts)
            retry_ok, retry_reason = _is_valid_summary(repaired_retry, facts)
            if retry_ok:
                logger.info(
                    "Project summary structural rewrite retry accepted for %s (initial_reason=%s)",
                    project_name,
                    reason,
                )
                repaired = repaired_retry
                ok = True
            else:
                logger.info(
                    "Project summary structural rewrite retry rejected for %s (initial_reason=%s, retry_reason=%s)",
                    project_name,
                    reason,
                    retry_reason,
                )

    if not ok:
        logger.warning(
            "llama-cpp project summary still invalid for %s (%s, elapsed=%.1fs)",
            project_name,
            reason,
            elapsed,
        )
        return None

    logger.info("Project summary llama-cpp finished for %s in %.1fs", project_name, elapsed)
    return repaired


def generate_project_summary(facts: dict[str, Any]) -> str | None:
    """
    Generate ML project summary from structured facts.

    Returns None if unavailable/invalid so caller can fallback to deterministic
    summary generation.
    """
    if not facts:
        return None

    cache_key = _facts_hash(facts)
    if _cache_enabled() and cache_key in _CACHE:
        logger.info("Project summary cache hit")
        return _CACHE[cache_key]

    def _use_deterministic_fallback(context: str) -> str | None:
        if _ml_required():
            return None
        fallback_summary = _validated_fallback_summary(facts, context=context)
        if not fallback_summary:
            return None
        if _cache_enabled():
            _CACHE[cache_key] = fallback_summary
        logger.info("Project summary generated from deterministic fallback")
        return fallback_summary

    llama_cpp_summary = _generate_project_summary_with_llama_cpp(facts)
    if llama_cpp_summary:
        if _cache_enabled():
            _CACHE[cache_key] = llama_cpp_summary
        logger.info("Project summary generated successfully via llama-cpp")
        return llama_cpp_summary

    if llama_cpp_enabled():
        logger.warning("llama-cpp project summary generation unavailable or invalid")
        return _use_deterministic_fallback(" after llama-cpp generation failure")

    model, tokenizer = _load_model()
    if model is None or tokenizer is None:
        logger.warning("Project summary skipped: model not available")
        return _use_deterministic_fallback(" after model unavailable")

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
        summary = _repair_summary(tokenizer.decode(output[0], skip_special_tokens=True), facts)
        if summary:
            ok, reason = _is_valid_summary(summary, facts)
            if ok:
                if _cache_enabled():
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
            summary = _repair_summary(tokenizer.decode(output[0], skip_special_tokens=True), facts)
            if summary:
                ok, reason = _is_valid_summary(summary, facts)
                if ok:
                    if _cache_enabled():
                        _CACHE[cache_key] = summary
                    logger.info("Project summary generated successfully (strict pass)")
                    return summary
                logger.warning("Project summary rejected after strict pass (%s): %s", reason, summary[:200])
        logger.warning("Project summary generation unavailable or invalid after ML passes")
        return _use_deterministic_fallback(" after ML validation failure")
    except Exception:
        logger.exception("Project summary generation failed")
        return _use_deterministic_fallback(" after exception")


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
    normalized_activity: list[tuple[str, float]] = []
    if activity_breakdown:
        for domain, pct in activity_breakdown:
            normalized_pct = _normalize_percentage(pct)
            if normalized_pct is None:
                continue
            normalized_activity.append((domain, normalized_pct))

    return {
        "project_name": project_name,
        "goal_terms": goal_terms[:4],
        "frameworks": frameworks[:4],
        "languages": languages[:3],
        "role": role,
        "role_description": role_description,
        "commit_focus": commit_focus,
        "commit_pct": _normalize_percentage(commit_pct),
        "line_pct": _normalize_percentage(line_pct),
        "activity_breakdown": normalized_activity,
    }
