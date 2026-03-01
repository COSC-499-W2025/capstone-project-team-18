import json
import os
import hashlib
import re
from typing import Any

from pydantic import BaseModel

from src.core.ML.models.azure_foundry_manager import AzureFoundryManager
from src.core.ML.models.azure_openai_runtime import azure_openai_enabled
from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.infrastructure.log.logging import get_logger
from src.core.ML.models.contribution_analysis.summary_constants import (
    SUMMARY_STYLE_EXAMPLE,
    SUMMARY_EXAMPLE_GUIDANCE,
    SUMMARY_BASE_PROMPT,
    SUMMARY_BANNED_PHRASES,
    SUMMARY_DOMAIN_KEYWORDS,
    SUMMARY_PHRASE_NORMALIZATION_REPLACEMENTS,
)

logger = get_logger(__name__)


class UserSummaryOutput(BaseModel):
    summary: str


class ExperienceStageOutput(BaseModel):
    stage: str
    confidence: float


USER_SUMMARY_PROMPT = """
You write concise professional portfolio summaries. Return strict JSON matching the provided schema.
Task: write a first-person developer summary using only FACTS_JSON.
Constraints:
- Exactly 3 sentences.
- 36 to 92 words total.
- Mention at least two anchors from facts across skills, languages, tools, role, or activities.
- Include delivery/outcome wording.
- Do not mention project names.
"""


EXPERIENCE_STAGE_PROMPT = """
Classify career stage from structured profile facts. Return strict JSON.
Pick one stage from: student, early-career, experienced.
Confidence must be between 0.0 and 1.0.
"""

USER_SUMMARY_DIVERSITY_REWRITE_PROMPT = """
Rewrite the user summary using the same facts but with clearly different wording and sentence flow.
Return strict JSON matching the provided schema.
Constraints:
- Exactly 3 sentences.
- Keep factual meaning aligned with FACTS_JSON.
- Do not mention project names.
- Do not include percentages.
"""

_CACHE: dict[str, str] = {}
_RECENT_USER_SUMMARIES: list[str] = []

_PROMPT_ECHO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*example\b", re.IGNORECASE),
    re.compile(r"\bexample\s*\d+\b", re.IGNORECASE),
    re.compile(r"\binput\s+draft\b", re.IGNORECASE),
    re.compile(r"\boutput\s+draft\b", re.IGNORECASE),
    re.compile(r"\boutput\s*:", re.IGNORECASE),
    re.compile(r"\bfollowing\s+context\b", re.IGNORECASE),
    re.compile(r"\byou\s+will\s+see\b", re.IGNORECASE),
    re.compile(r"\bafter\s+reading\b", re.IGNORECASE),
    re.compile(r"\bfacts_json\b", re.IGNORECASE),
    re.compile(r"\bhard\s+constraints?\b", re.IGNORECASE),
    re.compile(r"\breturn\s+exactly\b", re.IGNORECASE),
    re.compile(r"\bvalid\s+json\b", re.IGNORECASE),
    re.compile(r"\bjson\s+object\b", re.IGNORECASE),
    re.compile(r"\bschema\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+copy\b", re.IGNORECASE),
    re.compile(r"^\s*rewritten\b", re.IGNORECASE),
    re.compile(r"^\s*rewrite[d]?\s*:", re.IGNORECASE),
)


def _ml_required() -> bool:
    """
    Return whether callers explicitly require ML-generated summaries.

    When true, deterministic fallback summaries are disabled so the caller
    can enforce strict model-only behavior.
    """
    return os.environ.get("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML") == "1"


def _signature_diagnostics_enabled() -> bool:
    """Enable detailed signature-validator diagnostics via env."""
    raw = os.environ.get("ARTIFACT_MINER_SIGNATURE_DIAGNOSTICS")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _load_model():
    """Compatibility shim; local non-Azure model generation is removed."""
    return None, None


def _facts_hash(facts: dict[str, Any]) -> str:
    """Create a stable cache key for a facts payload."""
    serialized = json.dumps(facts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _cache_enabled() -> bool:
    """Allow disabling summary cache for strict per-run ML generation checks."""
    return os.environ.get("ARTIFACT_MINER_SUMMARY_CACHE_DISABLE", "0") != "1"


def _env_int(name: str, default: int) -> int:
    """Read integer env var safely."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    """Read float env var safely."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _summary_similarity(a: str, b: str) -> float:
    """Token-level Jaccard similarity for diversity checks."""
    a_tokens = set(re.findall(r"[a-z0-9]+", (a or "").lower()))
    b_tokens = set(re.findall(r"[a-z0-9]+", (b or "").lower()))
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def _summary_similarity_threshold() -> float:
    """Similarity threshold above which we attempt a rewrite."""
    return max(0.55, min(0.9, _env_float("ARTIFACT_MINER_USER_SUMMARY_SIMILARITY_THRESHOLD", 0.72)))


def _looks_too_similar_to_recent(summary: str) -> bool:
    """Return True if summary is too close to recent generated summaries."""
    if not summary or not _RECENT_USER_SUMMARIES:
        return False
    threshold = _summary_similarity_threshold()
    return any(_summary_similarity(summary, prev) >= threshold for prev in _RECENT_USER_SUMMARIES)


def _remember_user_summary(summary: str) -> None:
    """Store recent summaries for diversity checks."""
    if not summary:
        return
    _RECENT_USER_SUMMARIES.append(summary)
    if len(_RECENT_USER_SUMMARIES) > 20:
        del _RECENT_USER_SUMMARIES[0: len(_RECENT_USER_SUMMARIES) - 20]


def _stage_classifier_enabled() -> bool:
    """Enable optional ML stage classification (default on)."""
    raw = os.environ.get("ARTIFACT_MINER_STAGE_CLASSIFIER_ENABLE", "1")
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def _stage_classifier_min_confidence() -> float:
    """Minimum confidence required to allow ML stage override."""
    return max(0.5, min(0.95, _env_float("ARTIFACT_MINER_STAGE_CLASSIFIER_MIN_CONF", 0.75)))


def _normalize_stage_label(value: str | None) -> str | None:
    """Normalize free-form stage labels into canonical values."""
    if not value:
        return None
    lowered = str(value).strip().lower()
    lowered = lowered.replace("_", " ").replace("-", " ")
    lowered = " ".join(lowered.split())

    if not lowered:
        return None

    if lowered in {"student", "entry level", "entry", "junior"}:
        return "student"
    if lowered in {"early career", "early", "entry to mid level", "mid level", "intermediate"}:
        return "early-career"
    if lowered in {"experienced", "senior", "advanced", "lead", "principal"}:
        return "experienced"

    if "entry" in lowered and "mid" in lowered:
        return "early-career"
    if "early" in lowered and "career" in lowered:
        return "early-career"
    if "student" in lowered or "junior" in lowered:
        return "student"
    if any(token in lowered for token in ("senior", "experienced", "lead", "principal", "advanced")):
        return "experienced"
    return None


def _parse_confidence(value: Any) -> float | None:
    """Parse confidence values from flexible numeric/string formats."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            raw = float(value)
        else:
            text = str(value).strip()
            if not text:
                return None
            percent_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
            if percent_match:
                raw = float(percent_match.group(1)) / 100.0
            else:
                numeric_match = re.search(r"(-?\d+(?:\.\d+)?)", text)
                if not numeric_match:
                    return None
                raw = float(numeric_match.group(1))
        if raw > 1.0:
            raw = raw / 100.0
        if raw < 0.0 or raw > 1.0:
            return None
        return raw
    except Exception:
        return None


def _build_stage_classifier_prompt(stage_facts: dict[str, Any]) -> str:
    """Prompt for ML stage classification."""
    facts_json = json.dumps(stage_facts, ensure_ascii=True)
    return (
        "TASK: EXPERIENCE_STAGE_CLASSIFICATION\n"
        "Classify the user's career stage using only FACTS_JSON.\n"
        "Return exactly one JSON object with schema:\n"
        '{"stage":"student|early-career|experienced","confidence":0.0,"rationale":"string"}\n'
        "Rules:\n"
        "- stage must be one of: student, early-career, experienced.\n"
        "- confidence must be a number between 0 and 1.\n"
        "- rationale must be concise and grounded in facts.\n"
        "- Output valid JSON only.\n\n"
        f"FACTS_JSON: {facts_json}"
    )


def _build_stage_classifier_plain_prompt(stage_facts: dict[str, Any]) -> str:
    """Plain-text fallback prompt for stage classification when JSON fails."""
    facts_json = json.dumps(stage_facts, ensure_ascii=True)
    return (
        "TASK: EXPERIENCE_STAGE_CLASSIFICATION\n"
        "Classify the user's career stage using only FACTS_JSON.\n"
        "Return one line in this format:\n"
        "stage=<student|early-career|experienced>; confidence=<0-1>; rationale=<short text>\n\n"
        f"FACTS_JSON: {facts_json}\n\n"
        "Result:"
    )


def _extract_stage_from_payload(payload: Any) -> tuple[str | None, float | None]:
    """Extract stage/confidence from tolerant payload shapes."""
    if not isinstance(payload, dict):
        return None, None

    stage_candidate: str | None = None
    confidence_candidate: float | None = None

    for key in ("stage", "experience_stage", "level", "seniority"):
        value = payload.get(key)
        if isinstance(value, str):
            normalized = _normalize_stage_label(value)
            if normalized:
                stage_candidate = normalized
                break

    for key in ("confidence", "score", "probability"):
        conf = _parse_confidence(payload.get(key))
        if conf is not None:
            confidence_candidate = conf
            break

    if stage_candidate and confidence_candidate is not None:
        return stage_candidate, confidence_candidate

    for value in payload.values():
        if isinstance(value, dict):
            nested_stage, nested_conf = _extract_stage_from_payload(value)
            if nested_stage:
                return nested_stage, nested_conf
        if isinstance(value, str) and not stage_candidate:
            normalized = _normalize_stage_label(value)
            if normalized:
                stage_candidate = normalized

    return stage_candidate, confidence_candidate


def _extract_stage_from_raw_text(raw_text: str) -> tuple[str | None, float | None]:
    """Recover stage/confidence from non-JSON model output."""
    if not raw_text:
        return None, None
    cleaned = _strip_markdown_fence(raw_text).strip()
    if not cleaned:
        return None, None

    try:
        payload = json.loads(cleaned)
        return _extract_stage_from_payload(payload)
    except Exception:
        pass

    stage: str | None = None
    confidence: float | None = None

    explicit_stage = re.search(
        r"\b(?:stage|experience[_\s-]*stage|level|seniority)\s*[:=]\s*([a-zA-Z\-\s]+)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if explicit_stage:
        stage = _normalize_stage_label(explicit_stage.group(1))

    if not stage:
        stage = _normalize_stage_label(cleaned)

    explicit_conf = re.search(
        r"\b(?:confidence|score|probability)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?\s*%?)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if explicit_conf:
        confidence = _parse_confidence(explicit_conf.group(1))

    return stage, confidence


def resolve_experience_stage_with_ml(
    *,
    baseline_stage: str,
    project_count: int | None,
    active_months: float | None,
    role: str | None,
    top_skills: list[str] | None,
    top_languages: list[str] | None,
    tools: list[str] | None,
    professional_project_count: int | None = None,
    experimental_project_count: int | None = None,
    educational_project_count: int | None = None,
) -> str:
    """
    Resolve stage using baseline + optional ML override with strict safety gates.

    ML may refine the stage only when confidence is high and it differs by at most
    one level from the deterministic baseline.
    """
    baseline = _normalize_stage_label(baseline_stage) or "early-career"
    if not _stage_classifier_enabled():
        return baseline
    if azure_openai_enabled() and ml_extraction_allowed():
        foundry = AzureFoundryManager()
        stage_facts: dict[str, Any] = {
            "baseline_stage": baseline,
            "project_count": int(project_count or 0),
            "active_months": round(float(active_months), 1) if active_months is not None else None,
            "role": role or "",
            "top_skills": (top_skills or [])[:4],
            "top_languages": (top_languages or [])[:4],
            "tools": (tools or [])[:4],
            "tone_counts": {
                "professional": int(professional_project_count or 0),
                "experimental": int(experimental_project_count or 0),
                "educational": int(educational_project_count or 0),
            },
        }
        response = foundry.process_request(
            user_input=f"FACTS_JSON: {json.dumps(stage_facts, ensure_ascii=True)}",
            system_prompt=EXPERIENCE_STAGE_PROMPT,
            response_model=ExperienceStageOutput,
            schema_name="experience_stage",
            max_tokens=80,
            temperature=0.0,
        )
        if response:
            normalized = _normalize_stage_label(response.stage)
            if normalized and response.confidence >= _stage_classifier_min_confidence():
                stage_levels = {"student": 0,
                                "early-career": 1, "experienced": 2}
                if normalized in stage_levels and baseline in stage_levels:
                    if abs(stage_levels[normalized] - stage_levels[baseline]) <= 1:
                        return normalized
        return baseline
    return baseline


def _proficiency_level_from_stage(experience_stage: str | None) -> str | None:
    """Map normalized stage to professional proficiency wording."""
    stage = _normalize_stage_label(experience_stage)
    if stage == "student":
        return "Entry-level"
    if stage == "early-career":
        return "Entry-to-mid-level"
    if stage == "experienced":
        return "Senior-level"
    return None


def _opening_mentions_proficiency(summary: str, facts: dict[str, Any]) -> bool:
    """Check if sentence 1 contains the expected proficiency phrase."""
    level = str(facts.get("proficiency_level") or "").strip()
    if not level:
        return True
    sentences = _split_sentences(summary)
    if not sentences:
        return False
    return level.lower() in sentences[0].lower()


def _ensure_proficiency_in_opening(summary: str, facts: dict[str, Any]) -> str:
    """
    Ensure sentence 1 carries proficiency level wording when available.

    This is a soft reshape and does not introduce new rejection paths.
    """
    level = str(facts.get("proficiency_level") or "").strip()
    if not level:
        return summary
    sentences = _split_sentences(summary)
    if not sentences:
        return summary
    first = sentences[0].strip()
    if not first:
        return summary
    if level.lower() in first.lower():
        return summary

    stage = _normalize_stage_label(facts.get("experience_stage"))

    if stage == "early-career" and re.search(r"(?i)^early-career\b", first):
        updated = re.sub(r"(?i)^early-career\b", level, first, count=1)
    elif stage == "experienced" and re.search(r"(?i)^experienced\b", first):
        updated = re.sub(r"(?i)^experienced\b", level, first, count=1)
    elif stage == "student" and re.search(r"(?i)\bcomputer science student\b", first):
        updated = re.sub(r"(?i)\bcomputer science student\b",
                         f"{level} Computer Science student", first, count=1)
    elif re.search(r"(?i)\bsoftware contributor\b", first):
        updated = re.sub(r"(?i)\bsoftware contributor\b",
                         f"{level} software contributor", first, count=1)
    elif re.search(r"(?i)\bsoftware engineer\b", first):
        updated = re.sub(r"(?i)\bsoftware engineer\b",
                         f"{level} software engineer", first, count=1)
    elif re.search(r"(?i)\b(top skills include|preferred language|coding projects)\b", first):
        updated = (
            f"{_stage_identity_phrase(stage, facts.get('role'))} "
            f"focused on {_focus_phrase(facts.get('focus'))}"
        )
    else:
        updated = (
            f"{_stage_identity_phrase(stage, facts.get('role'))} "
            f"focused on {_focus_phrase(facts.get('focus'))}"
        )

    sentences[0] = updated.strip()
    rebuilt = ". ".join(sentence.strip()
                        for sentence in sentences if sentence.strip())
    return f"{rebuilt}." if rebuilt else summary


def _stage_identity_phrase(stage: str | None, role: Any) -> str:
    """Return a stable identity phrase for deterministic fallbacks."""
    normalized_stage = _normalize_stage_label(stage)
    role_text = str(role or "").strip().lower()
    if "engineer" not in role_text and "developer" not in role_text and "contributor" not in role_text:
        role_text = "software engineer"

    if normalized_stage == "student":
        return "Entry-level Computer Science student"
    if normalized_stage == "experienced":
        return f"Senior-level {role_text}"
    return f"Entry-to-mid-level {role_text}"


def _focus_phrase(focus: Any) -> str:
    """Normalize focus into natural fallback wording."""
    raw = str(focus or "").strip().lower()
    if not raw:
        return "software delivery"
    mapping = {
        "ml": "machine learning systems",
        "machine learning": "machine learning systems",
        "ai": "applied AI systems",
        "analytics": "analytics platforms",
        "backend": "backend services",
    }
    return mapping.get(raw, raw)


def _build_grounded_fallback_summary(facts: dict[str, Any]) -> str:
    """Build deterministic 3-sentence summary when ML output is unavailable."""
    stage = facts.get("experience_stage")
    role = facts.get("role")
    focus = _focus_phrase(facts.get("focus"))
    sentence_one = (
        f"{_stage_identity_phrase(stage, role)} focused on {focus}, "
        "with hands-on experience delivering practical software solutions"
    )

    anchors: list[str] = []
    for group in ("top_skills", "top_languages", "tools"):
        for item in (facts.get(group) or []):
            token = str(item).strip()
            if token and token.lower() not in {a.lower() for a in anchors}:
                anchors.append(token)
            if len(anchors) >= 3:
                break
        if len(anchors) >= 3:
            break
    stack_text = ", ".join(anchors[:3]) if anchors else "core engineering tools"
    sentence_two = (
        f"I build and maintain solutions using {stack_text}, "
        "turning requirements into reliable implementations and measurable outcomes"
    )

    activities = [str(a).strip() for a in (facts.get("activities") or []) if str(a).strip()]
    activity_text = ", ".join(activities[:2]) if activities else "steady delivery and clear collaboration"
    emerging = [str(e).strip() for e in (facts.get("emerging") or []) if str(e).strip()]
    if emerging:
        sentence_three = (
            f"I deliver reliable outcomes through {activity_text} while continuing to grow in {emerging[0]}"
        )
    else:
        sentence_three = (
            f"I deliver reliable outcomes through {activity_text} and disciplined engineering execution"
        )

    return f"{sentence_one}. {sentence_two}. {sentence_three}."


def _repair_summary_with_grounded_fallback(
    summary: str,
    facts: dict[str, Any],
    *,
    allow_fallback: bool = True,
) -> str | None:
    """Normalize model text; optionally return deterministic fallback when empty."""
    repair_facts = dict(facts)
    recalculated_level = _proficiency_level_from_stage(repair_facts.get("experience_stage"))
    if recalculated_level:
        repair_facts["proficiency_level"] = recalculated_level

    normalized = _normalize_summary(summary or "")
    normalized = _remove_invalid_sentences(normalized, repair_facts.get("project_names", []))
    normalized = _polish_summary(normalized)
    normalized = _trim_to_sentences(normalized, max_sentences=3)
    normalized = _restore_anchor_casing(normalized, repair_facts)
    normalized = _ensure_proficiency_in_opening(normalized, repair_facts)
    normalized = _normalize_summary(normalized)
    if normalized:
        injected = _inject_delivery_signal(normalized, repair_facts)
        return injected or normalized

    if not allow_fallback:
        return None

    fallback = _build_grounded_fallback_summary(repair_facts)
    fallback = _normalize_summary(fallback)
    fallback = _remove_invalid_sentences(fallback, repair_facts.get("project_names", []))
    fallback = _polish_summary(fallback)
    fallback = _trim_to_sentences(fallback, max_sentences=3)
    fallback = _restore_anchor_casing(fallback, repair_facts)
    fallback = _ensure_proficiency_in_opening(fallback, repair_facts)
    fallback = _normalize_summary(fallback)
    return fallback or None


def _validated_fallback_summary(facts: dict[str, Any], *, context: str) -> str | None:
    """Build deterministic fallback summary and keep only validator-approved output."""
    fallback = _repair_summary_with_grounded_fallback("", facts, allow_fallback=True)
    if not fallback:
        return None
    ok, reason = _is_valid_summary(fallback, facts)
    if ok:
        return fallback
    logger.warning("Signature summary fallback rejected%s (%s)", context, reason)
    return None


def _build_prompt(facts: dict[str, Any], strict: bool = False, include_example: bool = True) -> str:
    """
    Build a constrained prompt that forces narrative output and avoids list repetition.
    Remove project names/tags from the prompt to prevent leakage.
    """
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    facts_json = json.dumps(prompt_facts, ensure_ascii=True)
    style_example = f"{SUMMARY_EXAMPLE_GUIDANCE}{SUMMARY_STYLE_EXAMPLE}"
    base = SUMMARY_BASE_PROMPT
    if strict:
        must_mention = ", ".join([str(x) for x in facts.get(
            "top_skills", []) + facts.get("top_languages", []) + facts.get("tools", [])][:4])
        base += (
            " Follow this structure strictly: "
            "Sentence 1: identity + focus. "
            "Sentence 2: experience + impact. "
            "Sentence 3: strengths (skills/tools) + communication/insights. "
            "Sentence 4-6 (optional): only if each adds distinct, non-redundant information supported by facts."
            f" You MUST mention at least one of these terms verbatim: {must_mention}."
        )
    if include_example:
        return f"{base}\n{style_example}\n\nFacts (JSON): {facts_json}\n\nSummary:"
    return f"{base}\n\nFacts (JSON): {facts_json}\n\nSummary:"


def _normalize_summary(text: str) -> str:
    """
    Normalize raw generated text into a single clean paragraph.

    The function removes common list headers and collapses whitespace so
    validator checks operate on predictable formatting.
    """
    cleaned = text.strip()

    # Strip prompt-echo artifacts when the model leaks instruction blocks.
    marker_patterns = (
        r"\bquestion\s*:",
        r"\banswer\s*:",
        r"\boutput\s*:",
        r"\bfacts_json\s*:",
        r"\bfacts\s*\(json\)\s*:",
        r"\bfinal\s+summary\s*:",
        r"\btask\s*:",
        r"\bconstraints\s*:",
    )
    first_marker: int | None = None
    for pattern in marker_patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if not match:
            continue
        marker_index = match.start()
        if first_marker is None or marker_index < first_marker:
            first_marker = marker_index
    if first_marker is not None:
        cleaned = cleaned[:first_marker].strip()

    cleaned = re.sub(r"^\s*(?:final\s+)?summary\s*:\s*",
                     "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:final\s+)?summary\s*:\s*",
                     "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("Skills:", "").replace("Tools:", "")
    cleaned = cleaned.replace("Languages:", "")
    return " ".join(cleaned.split())


def _remove_percentage_mentions(summary: str) -> str:
    """
    Remove percentage mentions from user summaries.

    User-level summaries should stay qualitative; project summaries can keep
    percentages separately.
    """
    if not summary:
        return summary

    cleaned = summary
    cleaned = re.sub(
        r"(?i)\b(?:about|around|roughly|approximately|nearly|over|under|more than|less than)?\s*"
        r"\d{1,3}(?:\.\d+)?\s*%",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\b(?:about|around|roughly|approximately|nearly|over|under|more than|less than)?\s*"
        r"\d{1,3}(?:\.\d+)?\s*percent\b",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\b(?:of|in)\s+(?:the\s+)?(?:activity|contributions?|commits?|lines?)\b", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s*,", ", ", cleaned)
    return cleaned


def _restore_anchor_casing(summary: str, facts: dict[str, Any]) -> str:
    """
    Restore original anchor casing (e.g., FastAPI) after normalization/rewrite.
    """
    if not summary:
        return summary

    anchors: list[str] = []
    for key in ("top_skills", "top_languages", "tools"):
        values = facts.get(key, []) or []
        for value in values:
            if isinstance(value, str) and value.strip():
                anchors.append(value.strip())

    restored = summary
    seen: set[str] = set()
    for anchor in anchors:
        lowered = anchor.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(lowered)}(?![A-Za-z0-9])", re.IGNORECASE)
        restored = pattern.sub(anchor, restored)
    return restored


def _is_prompt_echo_sentence(sentence: str) -> bool:
    """Return True when a sentence looks like leaked prompt/instruction text."""
    text = (sentence or "").strip()
    if not text:
        return False
    if re.match(r"^\s*rewritten\b", text, flags=re.IGNORECASE):
        return True
    return any(pattern.search(text) for pattern in _PROMPT_ECHO_PATTERNS)


def _contains_prompt_echo(summary: str) -> bool:
    """Detect prompt-echo artifacts anywhere in the summary body."""
    return any(_is_prompt_echo_sentence(sentence) for sentence in _split_sentences(summary))


def _needs_resume_style_polish(summary: str) -> tuple[bool, str]:
    """
    Detect prompt-leak/instructional artifacts that should trigger an ML rewrite.
    """
    lowered = summary.lower()
    if _contains_prompt_echo(summary):
        return True, "prompt_echo"
    if _contains_noise_artifact(summary):
        return True, "noise_artifact"
    if re.search(r"\b(question|answer)\s*[:\-]", lowered):
        return True, "qa_artifact"
    if re.search(r"\b(?:final\s+)?summary\s*[:\-]", lowered):
        return True, "summary_artifact"
    if "you can say" in lowered or "you should say" in lowered:
        return True, "instructional_tone"
    if _contains_second_person_profile_voice(summary):
        return True, "second_person_tone"
    if _has_mixed_person_voice(summary):
        return True, "mixed_person_voice"
    if _contains_meta_narration(summary):
        return True, "meta_narration"
    if "?" in summary:
        return True, "question_like_tone"
    question_starters = (
        "what", "how", "why", "which", "when", "where",
        "can", "could", "should", "would", "do", "does", "is", "are",
    )
    for sentence in _split_sentences(summary):
        starter = sentence.strip().lower()
        if starter.startswith(question_starters):
            return True, "question_like_tone"
    return False, "ok"


def _contains_generic_resume_phrasing(summary: str) -> bool:
    """Detect generic phrasing that weakens resume quality."""
    lowered = summary.lower()
    generic_patterns = (
        "specializing primarily",
        "proficient primarily",
        "expertise extends to",
        "emerging interest in",
        "i am proficient",
        "with a steady cadence in",
        "focused primarily on",
    )
    return any(pattern in lowered for pattern in generic_patterns)


def _contains_second_person_profile_voice(summary: str) -> bool:
    """Detect second-person profile narration that reads like model noise."""
    for sentence in _split_sentences(summary):
        lowered = sentence.strip().lower()
        if lowered.startswith("your "):
            return True
        if re.search(r"\bhoning your skills\b", lowered):
            return True
        if re.search(
            r"\byour (?:entry|early|senior|professional) (?:experience|background|profile)\b",
            lowered,
        ):
            return True
    return False


def _contains_meta_narration(summary: str) -> bool:
    """Detect meta commentary about the summary/profile instead of resume content."""
    lowered = summary.lower()
    meta_patterns = (
        r"\bthis (?:summary|profile|description)\b",
        r"\bthe (?:summary|profile|description)\b",
        r"\bbased on (?:the )?(?:facts|data|information)\b",
        r"\baccording to (?:the )?(?:facts|data|information)\b",
        r"\bthe user(?:'s)? profile\b",
        r"\bcandidate profile\b",
    )
    return any(re.search(pattern, lowered) for pattern in meta_patterns)


def _has_mixed_person_voice(summary: str) -> bool:
    """Reject mixed first-person and second-person voice in one summary."""
    lowered = summary.lower()
    has_first_person = bool(re.search(r"\b(i|my|me)\b", lowered))
    has_second_person = bool(re.search(r"\b(you|your)\b", lowered))
    return has_first_person and has_second_person


def _has_mixed_person_voice_with_you(summary: str) -> bool:
    """
    Detect mixed voice when second-person *subject* voice ("you") appears.

    This intentionally ignores possessive-only phrasing ("your profile ...")
    so those can be classified as second_person_tone when appropriate.
    """
    lowered = summary.lower()
    has_first_person = bool(re.search(r"\b(i|my|me)\b", lowered))
    has_second_person_you = bool(re.search(r"\byou\b", lowered))
    return has_first_person and has_second_person_you


def _contains_question_like_tone(summary: str) -> bool:
    """Detect question-like phrasing even when punctuation is normalized."""
    if "?" in summary:
        return True
    question_starters = (
        "what", "how", "why", "which", "when", "where",
        "can", "could", "should", "would", "do", "does", "is", "are",
    )
    for sentence in _split_sentences(summary):
        starter = sentence.strip().lower()
        if starter.startswith(question_starters):
            return True
    return False


def _log_signature_validation_rejection(reason: str, summary: str) -> None:
    """Emit validator diagnostics when enabled."""
    if not _signature_diagnostics_enabled():
        return
    logger.info(
        "Signature validator rejected summary (reason=%s, chars=%d, words=%d)",
        reason,
        len(summary or ""),
        len((summary or "").split()),
    )
    if reason == "mixed_person_voice":
        lowered = (summary or "").lower()
        logger.info(
            "Signature validator mixed-person details (has_first_person=%s, has_you=%s, has_your=%s)",
            bool(re.search(r"\b(i|my|me)\b", lowered)),
            bool(re.search(r"\byou\b", lowered)),
            bool(re.search(r"\byour\b", lowered)),
        )


def _contains_summary_artifact_marker(summary: str | None) -> bool:
    """Detect leaked formatting markers that should never appear in final prose."""
    lowered = (summary or "").lower()
    return bool(re.search(r"\b(?:final\s+)?summary\s*[:\-]", lowered))


def _has_incomplete_sentence_fragment(summary: str) -> bool:
    """Detect malformed fragment sentences (e.g., 'With an.')."""
    starters = {"with", "and", "or", "but",
                "so", "because", "while", "although"}
    dangling_endings = {
        "a", "an", "the",
        "and", "or", "but",
        "to", "for", "with", "of", "in", "on", "at", "by", "from",
    }
    for sentence in _split_sentences(summary):
        tokens = _tokenize_words(sentence)
        if not tokens:
            return True
        if tokens[-1] in dangling_endings:
            return True
        if len(tokens) <= 4 and tokens[0] in starters:
            return True
    return False


def _has_delivery_or_outcome_signal(summary: str) -> bool:
    """Require at least one concrete delivery/outcome signal."""
    lowered = summary.lower()
    direct_keywords = (
        "delivered",
        "delivering",
        "delivery",
        "ship",
        "shipped",
        "built",
        "implemented",
        "developed",
        "improved",
        "optimized",
        "automated",
        "scaled",
        "streamlined",
        "reliable",
        "reliability",
        "outcome",
        "outcomes",
        "impact",
        "measurable",
        "performance",
        "production",
        "results",
        "implementation",
        "execution",
        "improvement",
        "improvements",
        "gains",
    )
    if any(keyword in lowered for keyword in direct_keywords):
        return True

    action_verbs = (
        "reflects",
        "reflect",
        "demonstrates",
        "demonstrate",
        "shows",
        "show",
        "drives",
        "drive",
        "supports",
        "support",
        "advances",
        "advance",
        "maintains",
        "maintain",
        "applies",
        "apply",
    )
    engineering_nouns = (
        "outcome",
        "outcomes",
        "impact",
        "results",
        "reliability",
        "quality",
        "performance",
        "implementation",
        "execution",
        "workflow",
        "workflows",
        "service",
        "services",
        "system",
        "systems",
        "pipeline",
        "pipelines",
        "feature",
        "features",
    )
    has_action_verb = any(verb in lowered for verb in action_verbs)
    has_engineering_noun = any(noun in lowered for noun in engineering_nouns)
    return has_action_verb and has_engineering_noun


def _has_transition_phrase(sentence: str) -> bool:
    """Detect explicit transition phrases that smooth topic shifts."""
    lowered = sentence.lower()
    transition_patterns = (
        r"\balso\b",
        r"\bin addition\b",
        r"\balongside\b",
        r"\bas well\b",
        r"\bbeyond\b",
        r"\bwhile\b",
    )
    return any(re.search(pattern, lowered) for pattern in transition_patterns)


def _coherence_issues(summary: str) -> list[str]:
    """Return soft coherence issues used for ranking and optional polish."""
    sentences = _split_sentences(summary)
    if len(sentences) < 3:
        return ["missing_three_sentence_shape"]

    s1, s2, s3 = sentences[0], sentences[1], sentences[2]
    s1_lower = s1.lower()
    s3_lower = s3.lower()
    issues: list[str] = []

    # Penalize "third sentence starts a brand new summary" phrasing.
    restart_markers = (
        "with a strong foundation",
        "my journey",
        "leveraging ",
        "as an early-career",
        "as a ",
        "as an ",
        "focused on ",
        "specializing in",
    )
    if any(s3_lower.startswith(marker) for marker in restart_markers):
        issues.append("third_sentence_restart")

    # Penalize repeated identity framing across sentence 1 and 3.
    identity_markers = (
        "early-career",
        "experienced",
        "software contributor",
        "software engineer",
        "computer science student",
    )
    if any(marker in s1_lower for marker in identity_markers) and any(marker in s3_lower for marker in identity_markers):
        issues.append("repeated_identity")

    # Penalize abrupt domain switch in final sentence without transition.
    s2_domains = _sentence_domains(s2)
    s3_domains = _sentence_domains(s3)
    if s2_domains and s3_domains and not (s2_domains & s3_domains) and not _has_transition_phrase(s3):
        issues.append("abrupt_domain_shift")

    return issues


def _resume_quality_score(summary: str, facts: dict[str, Any]) -> int:
    """Score candidate summaries so the best ML phrasing is selected."""
    score = 0
    words = len(summary.split())
    sentences = _sentence_count(summary)
    anchors = (facts.get("top_skills", []) or []) + \
        (facts.get("top_languages", []) or []) + (facts.get("tools", []) or [])

    if sentences == 3:
        score += 3
    elif sentences in {2, 4}:
        score += 1

    if 45 <= words <= 85:
        score += 3
    elif 42 <= words <= 92:
        score += 2

    if anchors and _summary_mentions_any(summary, anchors):
        score += 2
    if _has_delivery_or_outcome_signal(summary):
        score += 2
    if not _contains_generic_resume_phrasing(summary):
        score += 2
    if not _contains_project_name(summary, facts.get("project_names", []) or []):
        score += 1
    needs_polish, _ = _needs_resume_style_polish(summary)
    if not needs_polish:
        score += 1
    if _opening_mentions_proficiency(summary, facts):
        score += 2
    elif facts.get("proficiency_level"):
        score -= 1

    coherence_issue_count = len(_coherence_issues(summary))
    if coherence_issue_count == 0:
        score += 2
    else:
        score -= min(6, coherence_issue_count * 2)

    return score


def _should_expand_after_rejection(reason: str) -> bool:
    """Return whether rejection reason indicates summary needs expansion."""
    if not reason:
        return False
    return (
        reason.startswith("word_count=")
        or reason.startswith("sentence_count=")
        or reason in {
            "missing_delivery_signal",
            "generic_resume_tone",
            "second_person_tone",
            "second_person_profile_voice",
            "mixed_person_voice",
            "meta_narration",
            "noise_artifact",
            "meta_summary_marker",
            "fragment_sentence",
        }
    )


def _inject_delivery_signal(summary: str, facts: dict[str, Any]) -> str | None:
    """
    Add a minimal grounded delivery/outcome clause when that is the sole blocker.

    This keeps ML phrasing intact while satisfying the validator's requirement
    for a concrete delivery signal.
    """
    if not summary:
        return None
    if _has_delivery_or_outcome_signal(summary):
        return summary

    sentences = _split_sentences(summary)
    if not sentences:
        return None

    target_idx = 1 if len(sentences) >= 2 else 0
    target = sentences[target_idx].strip().rstrip(".")
    if not target:
        return None

    patched = f"{target} delivering measurable outcomes through reliable implementation."
    sentences[target_idx] = patched
    rebuilt = ". ".join(s.strip().rstrip(".")
                        for s in sentences if s.strip()) + "."
    rebuilt = _normalize_summary(rebuilt)
    rebuilt = _remove_invalid_sentences(
        rebuilt, facts.get("project_names", []))
    rebuilt = _polish_summary(rebuilt)
    rebuilt = _trim_to_sentences(rebuilt, max_sentences=3)
    rebuilt = _ensure_proficiency_in_opening(rebuilt, facts)
    rebuilt = _normalize_summary(rebuilt)
    return rebuilt or None


def _select_best_summary_candidate(candidates: list[str], facts: dict[str, Any]) -> str | None:
    """Normalize and rank candidate summaries, returning the strongest option."""
    best: str | None = None
    best_score = -1
    seen: set[str] = set()

    for candidate in candidates:
        normalized = _normalize_summary(candidate or "")
        normalized = _remove_invalid_sentences(
            normalized, facts.get("project_names", []))
        normalized = _polish_summary(normalized)
        normalized = _trim_to_sentences(normalized, max_sentences=3)
        normalized = _restore_anchor_casing(normalized, facts)
        normalized = _ensure_proficiency_in_opening(normalized, facts)
        normalized = _normalize_summary(normalized)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)

        score = _resume_quality_score(normalized, facts)
        is_ok, _reason = _is_valid_summary(normalized, facts)
        if is_ok:
            score += 100
        if score > best_score:
            best = normalized
            best_score = score

    return best


def _is_list_like(text: str) -> bool:
    """Heuristic: detect bullet/list style outputs instead of narrative prose."""
    lowered = text.lower()
    if "skills:" in lowered or "tools:" in lowered or "languages:" in lowered:
        return True
    if re.search(r"\b(question|answer)\s*[:\-]", lowered):
        return True
    if "you can say" in lowered or "you should say" in lowered:
        return True
    if "\n-" in text or "\n•" in text:
        return True
    return False


def _is_noisy_sentence(sentence: str) -> bool:
    """
    Detect broad prompt/instruction/meta noise patterns in a sentence.

    This intentionally combines multiple weak heuristics to catch new variants
    without relying on one fixed phrase.
    """
    text = (sentence or "").strip()
    if not text:
        return True
    lowered = text.lower()

    if _is_prompt_echo_sentence(text):
        return True
    if _contains_second_person_profile_voice(text):
        return True
    if _contains_meta_narration(text):
        return True
    if _has_mixed_person_voice(text):
        return True

    # Common rewrite/meta lead-ins produced by polishing prompts.
    if re.match(r"^\s*(?:rewritten?|revised|refined|improved|updated)\b", lowered):
        return True

    # Label-like artifacts: "Rewrite:", "Response:", "Version 2:", etc.
    if re.match(
        r"^\s*(?:rewrite|rewritten|revision|response|output|draft|version(?:\s*\d+)?)\s*[:\-]",
        lowered,
    ):
        return True

    # Keep question-style and direct instruction language out of final prose.
    if "?" in text:
        return True
    if re.search(r"\b(?:you can|you should|please|ensure|make sure|must)\b", lowered):
        return True

    return False


def _contains_noise_artifact(summary: str) -> bool:
    """Return True if any sentence contains generalized noise artifacts."""
    return any(_is_noisy_sentence(sentence) for sentence in _split_sentences(summary))


def _remove_invalid_sentences(text: str, project_names: list[str] | None = None) -> str:
    """
    Remove sentences that violate tone/safety constraints.

    This strips assistant meta-language, generic filler, and any sentence that
    leaks explicit project names from the facts payload.
    """
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    kept = []
    for s in sentences:
        lowered = s.lower()
        if _is_noisy_sentence(s):
            continue
        if any(bad in lowered for bad in SUMMARY_BANNED_PHRASES):
            continue
        if _is_prompt_echo_sentence(s):
            continue
        if re.search(r"\b(question|answer)\s*[:\-]", lowered):
            continue
        if re.search(r"\b(?:final\s+)?summary\s*[:\-]", lowered):
            continue
        if lowered.startswith("you can say ") or lowered.startswith("you should say "):
            continue
        if _contains_second_person_profile_voice(s):
            continue
        if _has_mixed_person_voice(s):
            continue
        if _contains_meta_narration(s):
            continue
        if project_names and _contains_project_name(s, project_names):
            continue
        kept.append(s)
    if not kept:
        return ""
    return ". ".join(kept) + "."


def _trim_to_sentences(text: str, max_sentences: int = 4) -> str:
    """Trim output to a maximum sentence count while preserving punctuation."""
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if not sentences:
        return text
    trimmed = ". ".join(sentences[:max_sentences])
    if text.endswith(".") or len(sentences) <= max_sentences:
        return trimmed + "."
    return trimmed + "."


def _normalize_token(token: str) -> str:
    """Normalize a token for loose matching by removing non-alphanumeric chars."""
    return "".join(ch for ch in token.lower() if ch.isalnum())


def _tokenize_words(text: str) -> list[str]:
    """Tokenize text for overlap/duplication heuristics."""
    return [tok for tok in re.findall(r"[a-z0-9+#]+", text.lower()) if tok]


def _split_sentences(text: str) -> list[str]:
    """Split free-form text into sentence-like chunks."""
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


def _sentence_count(text: str) -> int:
    """Count sentence-like segments using punctuation boundaries."""
    return len(_split_sentences(text))


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute token-set overlap used for near-duplicate detection."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _ngrams(tokens: list[str], n: int = 4) -> set[tuple[str, ...]]:
    """Build n-gram tuples so phrase-level duplicates can be detected."""
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def _sentence_domains(sentence: str) -> set[str]:
    """
    Map a sentence to coarse semantic domains (web/data/mobile/backend/ml).

    Domain tags are used to avoid restating the same high-level profile point
    across multiple sentences.
    """
    lowered = sentence.lower()
    domains: set[str] = set()
    for domain, keywords in SUMMARY_DOMAIN_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            domains.add(domain)
    return domains


def _canonicalize_phrase_repetition(text: str) -> str:
    """
    Normalize known repetitive phrase patterns to a single canonical form.

    This improves dedup reliability for common verbose patterns observed in
    generated summaries.
    """
    updated = text
    for pattern, replacement in SUMMARY_PHRASE_NORMALIZATION_REPLACEMENTS:
        updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
    return updated


def _polish_summary(summary: str) -> str:
    """
    Remove repeated ideas and tighten wording without introducing new facts.
    """
    if not summary:
        return summary

    summary = _canonicalize_phrase_repetition(summary)
    raw_sentences = _split_sentences(summary)
    if not raw_sentences:
        return summary

    kept: list[str] = []
    seen_sentence_keys: set[str] = set()
    seen_domains: set[str] = set()

    for sentence in raw_sentences:
        sentence_token_list = _tokenize_words(sentence)
        sentence_tokens = set(sentence_token_list)
        if not sentence_tokens:
            continue
        sentence_ngrams = _ngrams(sentence_token_list, n=4)

        sentence_key = " ".join(sorted(sentence_tokens))
        if sentence_key in seen_sentence_keys:
            continue

        sentence_domains = _sentence_domains(sentence)
        near_duplicate = False
        for existing in kept:
            existing_token_list = _tokenize_words(existing)
            existing_tokens = set(existing_token_list)
            existing_ngrams = _ngrams(existing_token_list, n=4)
            if _jaccard_similarity(sentence_tokens, existing_tokens) < 0.62:
                # Catch phrase-level duplicates even when sentence wording differs.
                if _sentence_domains(existing) & sentence_domains and (sentence_ngrams & existing_ngrams):
                    near_duplicate = True
                    break
                continue
            if _sentence_domains(existing) & sentence_domains:
                near_duplicate = True
                break
        if near_duplicate:
            continue

        kept.append(sentence)
        seen_sentence_keys.add(sentence_key)
        seen_domains.update(sentence_domains)

    if not kept:
        return ""
    return ". ".join(kept) + "."


def _summary_mentions_any(summary: str, items: list[str]) -> bool:
    """Check whether summary references at least one expected anchor term."""
    lowered = summary.lower()
    normalized_summary = _normalize_token(summary)
    summary_tokens = {_normalize_token(
        tok) for tok in re.findall(r"[a-zA-Z0-9]+", summary)}
    summary_tokens.discard("")
    low_signal_tokens = {
        "tool", "tools", "skill", "skills", "language", "languages",
        "stack", "tech", "technology", "technologies", "framework", "frameworks",
    }
    for item in items:
        if not item:
            continue
        item_lower = str(item).lower()
        if item_lower in lowered:
            return True
        normalized_item = _normalize_token(item_lower)
        if normalized_item and normalized_item in normalized_summary:
            return True

        item_tokens = {_normalize_token(tok) for tok in re.findall(
            r"[a-zA-Z0-9]+", item_lower)}
        item_tokens.discard("")
        if not item_tokens or not summary_tokens:
            continue

        informative_tokens = {
            tok for tok in item_tokens if len(tok) >= 4 and tok not in low_signal_tokens
        }
        required_tokens = informative_tokens or item_tokens
        overlap = required_tokens & summary_tokens
        if not overlap:
            continue

        coverage = len(overlap) / len(required_tokens)
        if coverage >= 0.5:
            return True
        if len(required_tokens) >= 3 and len(overlap) >= 2:
            return True
        if len(required_tokens) == 1:
            return True
    return False


def _anchor_coverage_count(summary: str, facts: dict[str, Any]) -> int:
    """Count how many distinct anchor groups are referenced in the summary."""
    groups = {
        "skills": facts.get("top_skills", []) or [],
        "languages": facts.get("top_languages", []) or [],
        "tools": facts.get("tools", []) or [],
        "role": [facts.get("role")] if facts.get("role") else [],
        "activities": facts.get("activities", []) or [],
    }
    covered = 0
    for items in groups.values():
        normalized_items = [str(x).strip() for x in items if str(x).strip()]
        if normalized_items and _summary_mentions_any(summary, normalized_items):
            covered += 1
    return covered


def _has_redundant_repetition(summary: str) -> bool:
    """Detect repeated sentence content in generated summaries."""
    sentences = [s.strip().lower() for s in _split_sentences(summary) if s.strip()]
    if len(sentences) < 2:
        return False
    if len(set(sentences)) != len(sentences):
        return True

    for idx in range(1, len(sentences)):
        prev_tokens = set(_tokenize_words(sentences[idx - 1]))
        curr_tokens = set(_tokenize_words(sentences[idx]))
        if not prev_tokens or not curr_tokens:
            continue
        overlap = len(prev_tokens & curr_tokens) / len(prev_tokens | curr_tokens)
        if overlap >= 0.85:
            return True
    return False


def _contains_example_overlap(summary: str) -> bool:
    # Reject if summary overlaps 5+ consecutive words from the example.
    def _tokens(text: str) -> list[str]:
        return [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if t]

    summary_tokens = _tokens(summary)
    example_tokens = _tokens(SUMMARY_STYLE_EXAMPLE)

    if len(summary_tokens) < 5 or len(example_tokens) < 5:
        return False

    example_ngrams = set(
        " ".join(example_tokens[i:i+5]) for i in range(len(example_tokens) - 4)
    )
    for i in range(len(summary_tokens) - 4):
        if " ".join(summary_tokens[i:i+5]) in example_ngrams:
            return True
    return False


def _contains_project_name(summary: str, project_names: list[str]) -> bool:
    """Return true if summary leaks a project name or close alias from facts."""
    lowered = summary.lower()
    summary_tokens = _tokenize_words(summary)
    summary_joined = f" {' '.join(summary_tokens)} "
    generic_tokens = {
        "app",
        "apps",
        "service",
        "services",
        "project",
        "projects",
        "backend",
        "frontend",
        "mobile",
        "web",
        "portal",
        "tracker",
        "pipeline",
        "lab",
    }

    for name in project_names:
        if not name:
            continue
        name_lower = str(name).lower()
        if name_lower in lowered:
            return True

        name_tokens = [
            _normalize_token(tok)
            for tok in re.findall(r"[A-Za-z0-9]+", name_lower)
        ]
        name_tokens = [tok for tok in name_tokens if tok]
        if len(name_tokens) < 2:
            continue

        full_alias = " ".join(name_tokens)
        if f" {full_alias} " in summary_joined:
            return True

        tail_pair = name_tokens[-2:]
        if len(tail_pair) == 2:
            if not (tail_pair[0] in generic_tokens and tail_pair[1] in generic_tokens):
                tail_alias = " ".join(tail_pair)
                if f" {tail_alias} " in summary_joined:
                    return True
    return False


def _extract_summary_from_payload(payload: Any) -> str | None:
    """Extract summary text from tolerant payload shapes."""
    if not isinstance(payload, dict):
        return None

    direct = payload.get("summary")
    if isinstance(direct, str):
        return direct

    for key in ("result", "response", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = _extract_summary_from_payload(value)
            if nested:
                return nested

    for value in payload.values():
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            nested = _extract_summary_from_payload(value)
            if nested:
                return nested
    return None


def _strip_markdown_fence(text: str) -> str:
    """Remove single code-fence wrappers around model output."""
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
    """Recover summary text when model output is not valid JSON."""
    if not raw_text:
        return None

    cleaned = _strip_markdown_fence(raw_text)
    if not cleaned:
        return None

    # Sometimes the model still returns JSON-ish text in plain mode.
    try:
        payload = json.loads(cleaned)
        summary = _extract_summary_from_payload(payload)
        if summary:
            return summary
    except Exception:
        pass

    # Strip common label wrappers.
    cleaned = re.sub(r"^\s*(?:final\s+)?summary\s*:\s*",
                     "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:final\s+)?summary\s*:\s*", "",
                     cleaned, flags=re.IGNORECASE).strip()
    return cleaned or None


def _is_valid_summary(summary: str, facts: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(summary, str):
        return False, "not_string"
    if not summary.strip():
        return False, "empty_summary"
    if _is_list_like(summary):
        return False, "list_like"
    if _contains_prompt_echo(summary):
        return False, "prompt_echo"
    if _contains_question_like_tone(summary):
        return False, "question_like_tone"
    if re.search(r"\byour\s+profile\b", summary.lower()):
        return False, "second_person_tone"
    if _has_mixed_person_voice_with_you(summary):
        _log_signature_validation_rejection("mixed_person_voice", summary)
        return False, "mixed_person_voice"
    if _contains_noise_artifact(summary):
        return False, "noise_artifact"
    if _contains_summary_artifact_marker(summary):
        return False, "meta_summary_marker"
    if _has_incomplete_sentence_fragment(summary):
        return False, "fragment_sentence"
    needs_polish, polish_reason = _needs_resume_style_polish(summary)
    if needs_polish:
        return False, polish_reason
    min_words = 38 if _ml_required() else 36
    max_words = 92 if _ml_required() else 110
    word_count = len(summary.split())
    if word_count < min_words or word_count > max_words:
        return False, f"word_count={word_count}"
    sentence_count = _sentence_count(summary)
    if sentence_count != 3:
        return False, f"sentence_count={sentence_count}"

    if _contains_generic_resume_phrasing(summary):
        if _anchor_coverage_count(summary, facts) < 2:
            return False, "generic_resume_tone"
    if re.search(r"(?i)\b\d{1,3}(?:\.\d+)?\s*%|\b\d{1,3}(?:\.\d+)?\s*percent\b", summary):
        return False, "contains_percentage"
    if _contains_second_person_profile_voice(summary):
        return False, "second_person_profile_voice"
    if _has_mixed_person_voice(summary):
        return False, "mixed_person_voice"
    if _contains_meta_narration(summary):
        return False, "meta_narration"
    if not _has_delivery_or_outcome_signal(summary):
        return False, "missing_delivery_signal"

    project_names = facts.get("project_names", [])
    if _contains_project_name(summary, project_names):
        return False, "mentions_project_name"

    skills = facts.get("top_skills", [])
    langs = facts.get("top_languages", [])
    tools = facts.get("tools", [])
    anchors = skills + langs + tools
    if anchors and not _summary_mentions_any(summary, anchors):
        return False, "no_skill_language_tool_anchor"
    if _anchor_coverage_count(summary, facts) < 2:
        return False, "insufficient_anchor_coverage"
    if _contains_example_overlap(summary):
        return False, "example_overlap"
    if _has_redundant_repetition(summary):
        return False, "redundant_repetition"
    return True, "ok"


def _generate_signature_with_azure_openai(facts: dict[str, Any]) -> str | None:
    """Generate signature summary via Azure OpenAI structured outputs."""
    if not azure_openai_enabled() or not ml_extraction_allowed():
        return None
    if os.environ.get("ARTIFACT_MINER_DISABLE_SIGNATURE_MODEL") == "1":
        return None

    foundry = AzureFoundryManager()
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    response = foundry.process_request(
        user_input=f"FACTS_JSON: {json.dumps(prompt_facts, ensure_ascii=True)}",
        system_prompt=USER_SUMMARY_PROMPT,
        response_model=UserSummaryOutput,
        schema_name="signature_summary",
        max_tokens=180,
        temperature=0.0,
    )
    if response is None:
        logger.warning(
            "[TASK=USER_SUMMARY] Azure generation returned no structured response")
        return None
    repaired = _repair_summary_with_grounded_fallback(
        response.summary, facts, allow_fallback=False)
    if not repaired:
        logger.warning(
            "[TASK=USER_SUMMARY] Azure output could not be repaired")
        return None
    ok, reason = _is_valid_summary(repaired, facts)
    if not ok:
        logger.warning(
            "[TASK=USER_SUMMARY] Azure output rejected by validator (reason=%s)", reason)
        if reason == "generic_resume_tone":
            # One targeted retry to make the summary more fact-anchored.
            retry = foundry.process_request(
                user_input=(
                    f"FACTS_JSON: {json.dumps(prompt_facts, ensure_ascii=True)}\n\n"
                    f"DRAFT_SUMMARY: {repaired}\n\n"
                    "Rewrite to be specific to this profile. Mention at least two concrete anchors "
                    "from skills/languages/tools/role/activities."
                ),
                system_prompt=USER_SUMMARY_DIVERSITY_REWRITE_PROMPT,
                response_model=UserSummaryOutput,
                schema_name="signature_summary_generic_retry",
                max_tokens=180,
                temperature=0.0,
            )
            if retry and retry.summary:
                retried = _repair_summary_with_grounded_fallback(
                    retry.summary, facts, allow_fallback=False)
                if retried:
                    retry_ok, retry_reason = _is_valid_summary(retried, facts)
                    if retry_ok:
                        logger.info(
                            "[TASK=USER_SUMMARY] Azure generic-tone retry accepted")
                        return retried
                    logger.warning(
                        "[TASK=USER_SUMMARY] Azure generic-tone retry rejected (reason=%s)", retry_reason)
    return repaired if ok else None


def _rewrite_summary_for_diversity_if_needed(summary: str, facts: dict[str, Any]) -> str:
    """
    When summary is too similar to recent outputs, try one Azure rewrite pass.

    Falls back to the original summary on any failure to preserve safety.
    """
    if not summary:
        return summary
    if not _looks_too_similar_to_recent(summary):
        return summary
    if not (azure_openai_enabled() and ml_extraction_allowed()):
        return summary

    try:
        foundry = AzureFoundryManager()
        prompt_facts = dict(facts)
        prompt_facts.pop("project_names", None)
        prompt_facts.pop("tags", None)
        response = foundry.process_request(
            user_input=(
                f"FACTS_JSON: {json.dumps(prompt_facts, ensure_ascii=True)}\n\n"
                f"CURRENT_SUMMARY: {summary}"
            ),
            system_prompt=USER_SUMMARY_DIVERSITY_REWRITE_PROMPT,
            response_model=UserSummaryOutput,
            schema_name="signature_summary_diversity_rewrite",
            max_tokens=180,
            temperature=0.4,
        )
        if response is None or not response.summary:
            return summary
        candidate = _repair_summary_with_grounded_fallback(
            response.summary, facts, allow_fallback=False)
        if not candidate:
            return summary
        ok, _reason = _is_valid_summary(candidate, facts)
        if not ok:
            return summary
        if _summary_similarity(candidate, summary) >= _summary_similarity_threshold():
            return summary
        logger.info("[TASK=USER_SUMMARY] Diversity rewrite applied")
        return candidate
    except Exception:
        logger.exception("User summary diversity rewrite failed")
        return summary


def generate_signature(facts: dict[str, Any]) -> str | None:
    """
    Generate a dynamic developer signature using a local LLM.
    Returns None if ML is disabled or model fails.
    """
    if not facts:
        return None

    cache_key = _facts_hash(facts)
    if _cache_enabled() and cache_key in _CACHE:
        logger.info("Signature summary cache hit")
        cached = _CACHE[cache_key]
        _remember_user_summary(cached)
        return cached

    if azure_openai_enabled():
        azure_summary = _generate_signature_with_azure_openai(facts)
        if azure_summary:
            azure_summary = _rewrite_summary_for_diversity_if_needed(
                azure_summary, facts)
            if _cache_enabled():
                _CACHE[cache_key] = azure_summary
            _remember_user_summary(azure_summary)
            logger.info(
                "[TASK=USER_SUMMARY] Generated successfully via Azure OpenAI")
            return azure_summary
        if _ml_required():
            return None
        fallback_summary = _validated_fallback_summary(
            facts, context=" after Azure generation failure")
        if fallback_summary:
            _remember_user_summary(fallback_summary)
            logger.info(
                "[TASK=USER_SUMMARY] Generated from deterministic fallback")
            return fallback_summary
        return None

    logger.info("Signature local-model path removed; using deterministic fallback")
    if _ml_required():
        return None
    fallback_summary = _validated_fallback_summary(facts, context="")
    if fallback_summary:
        _remember_user_summary(fallback_summary)
        logger.info("Signature summary generated from deterministic fallback")
        return fallback_summary
    return None


def build_signature_facts(
    focus: str | None,
    top_skills: list[str],
    top_languages: list[str],
    tools: list[str],
    role: str | None,
    cadence: str | None,
    commit_focus: str | None,
    themes: list[str] | None,
    activities: list[str] | None,
    emerging: list[str] | None,
    project_names: list[str] | None,
    tags: list[str] | None,
    experience_stage: str | None = None,
) -> dict[str, Any]:
    """
    Build a minimal facts payload for signature generation.
    Keep fields compact to reduce hallucination risk.
    """
    normalized_stage = _normalize_stage_label(experience_stage)
    proficiency_level = _proficiency_level_from_stage(normalized_stage)
    facts: dict[str, Any] = {
        "focus": focus,
        "top_skills": top_skills[:3],
        "top_languages": top_languages[:3],
        "tools": tools[:3],
        "role": role or "contributor",
        "cadence": cadence or "steady",
        "commit_focus": commit_focus,
        "themes": themes[:4] if themes else [],
        "activities": activities[:4] if activities else [],
        "emerging": emerging[:3] if emerging else [],
        "project_names": project_names[:6] if project_names else [],
        "tags": tags[:8] if tags else [],
        "experience_stage": normalized_stage,
        "proficiency_level": proficiency_level,
    }
    return facts
