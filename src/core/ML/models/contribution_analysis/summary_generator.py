import json
import os
import hashlib
import re
from time import perf_counter
from typing import Any

from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.core.ML.models.model_runtime import cuda_available, get_causal_lm
from src.core.ML.models.llama_cpp_runtime import (
    llama_cpp_enabled,
    resolve_llama_cpp_model_path,
    llama_cpp_generate_json_object,
    llama_cpp_generate_text,
)
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

_MODEL = None
_TOKENIZER = None
_MODEL_FAILED = False
_CACHE: dict[str, str] = {}

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
    if raw is None:
        raw = os.environ.get("ARTIFACT_MINER_LLAMA_CPP_DIAGNOSTICS")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _get_model_name() -> str:
    # If no explicit override, choose a smaller model on CPU to avoid OOM.
    override = os.environ.get("ARTIFACT_MINER_SIGNATURE_MODEL")
    if override:
        return override

    if cuda_available():
        return "microsoft/Phi-3-mini-4k-instruct"

    # CPU-friendly default (smaller, faster, lower memory)
    return "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def _load_model():
    global _MODEL, _TOKENIZER, _MODEL_FAILED

    if not ml_extraction_allowed():
        return None, None

    if os.environ.get("ARTIFACT_MINER_DISABLE_SIGNATURE_MODEL") == "1":
        logger.info("Signature model disabled via env variable")
        return None, None

    if _MODEL_FAILED:
        return None, None

    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER

    try:
        model_name = _get_model_name()
        logger.info("Loading signature model: %s", model_name)
        model, tokenizer = get_causal_lm(model_name)
        if model is None or tokenizer is None:
            _MODEL_FAILED = True
            return None, None

        _MODEL = model
        _TOKENIZER = tokenizer
        return _MODEL, _TOKENIZER
    except Exception:
        logger.exception("Failed to load signature model")
        _MODEL_FAILED = True
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


def _llama_cpp_max_tokens() -> int:
    """
    Keep user-summary generation bounded so CLI remains responsive.
    """
    return max(64, min(180, _env_int("ARTIFACT_MINER_SIGNATURE_LLAMA_MAX_TOKENS", 112)))


def _llama_cpp_max_retries() -> int:
    """
    Keep retries low; repaired fallback now handles many malformed outputs.
    """
    return max(0, min(2, _env_int("ARTIFACT_MINER_SIGNATURE_LLAMA_MAX_RETRIES", 2)))


def _llama_cpp_max_seconds() -> float:
    """Upper budget for user-summary llama-cpp generation attempts."""
    return max(10.0, _env_float("ARTIFACT_MINER_SIGNATURE_LLAMA_MAX_SEC", 75.0))


def _llama_cpp_model_path() -> str | None:
    """Resolve GGUF model path for user summary generation."""
    return resolve_llama_cpp_model_path("ARTIFACT_MINER_LLAMA_CPP_SIGNATURE_MODEL_PATH")


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
    if not llama_cpp_enabled() or not ml_extraction_allowed():
        return baseline

    model_path = _llama_cpp_model_path()
    if not model_path:
        return baseline

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

    min_conf = _stage_classifier_min_confidence()
    stage_levels = {"student": 0, "early-career": 1, "experienced": 2}
    candidate_stage: str | None = None
    candidate_conf: float | None = None

    def _validator(payload: dict[str, Any]) -> tuple[bool, str]:
        stage, conf = _extract_stage_from_payload(payload)
        if not stage:
            return False, "missing_stage"
        if conf is None:
            return False, "missing_confidence"
        if conf < 0.0 or conf > 1.0:
            return False, "confidence_out_of_range"
        return True, "ok"

    response = llama_cpp_generate_json_object(
        model_path=model_path,
        prompt=_build_stage_classifier_prompt(stage_facts),
        validator=_validator,
        max_retries=1,
        max_tokens=max(56, min(120, _llama_cpp_max_tokens())),
        temperature=0.0,
        top_p=0.95,
        max_total_seconds=max(6.0, min(18.0, _llama_cpp_max_seconds() / 3.0)),
    )
    if isinstance(response, dict):
        candidate_stage, candidate_conf = _extract_stage_from_payload(response)

    if not candidate_stage:
        raw_text = llama_cpp_generate_text(
            model_path=model_path,
            prompt=_build_stage_classifier_plain_prompt(stage_facts),
            max_retries=0,
            max_tokens=96,
            temperature=0.0,
            top_p=0.95,
            max_total_seconds=max(4.0, min(10.0, _llama_cpp_max_seconds() / 4.0)),
        )
        if raw_text:
            candidate_stage, candidate_conf = _extract_stage_from_raw_text(raw_text)

    if not candidate_stage:
        return baseline
    candidate_stage = _normalize_stage_label(candidate_stage)
    if not candidate_stage or candidate_stage not in stage_levels:
        return baseline

    # Same stage is always safe.
    if candidate_stage == baseline:
        return baseline

    # Cross-level overrides require confidence + adjacency safety gate.
    distance = abs(stage_levels[candidate_stage] - stage_levels[baseline])
    if distance > 1:
        return baseline
    if candidate_conf is None or candidate_conf < min_conf:
        return baseline

    return candidate_stage


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
        updated = re.sub(r"(?i)\bcomputer science student\b", f"{level} Computer Science student", first, count=1)
    elif re.search(r"(?i)\bsoftware contributor\b", first):
        updated = re.sub(r"(?i)\bsoftware contributor\b", f"{level} software contributor", first, count=1)
    elif re.search(r"(?i)\bsoftware engineer\b", first):
        updated = re.sub(r"(?i)\bsoftware engineer\b", f"{level} software engineer", first, count=1)
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
    rebuilt = ". ".join(sentence.strip() for sentence in sentences if sentence.strip())
    return f"{rebuilt}." if rebuilt else summary


def _build_llama_cpp_prompt(facts: dict[str, Any]) -> str:
    """
    Build strict structured prompt for llama-cpp summary generation.
    """
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    facts_json = json.dumps(prompt_facts, ensure_ascii=True)
    proficiency_line = ""
    if prompt_facts.get("proficiency_level"):
        proficiency_line = (
            "- Sentence 1 must include the exact proficiency_level phrase when provided.\n"
        )
    return (
        "TASK: USER_SUMMARY\n"
        "Return exactly one JSON object with this schema:\n"
        '{"summary":"string"}\n'
        "Hard constraints:\n"
        "- Exactly 3 sentences.\n"
        "- 38 to 92 words.\n"
        "- Narrative prose only (no lists or bullets).\n"
        "- Use only the facts in the payload.\n"
        "- Mention at least one concrete stack term from top_skills/top_languages/tools when available.\n"
        f"{proficiency_line}"
        "- Do not mention project names, company names, or being an assistant.\n"
        "- Do not include any key besides summary.\n"
        "- Output must be valid JSON and nothing else.\n\n"
        f"FACTS_JSON: {facts_json}"
    )


def _build_llama_cpp_plain_prompt(facts: dict[str, Any]) -> str:
    """
    Build plain-text prompt for recovery when structured JSON output fails.
    """
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    facts_json = json.dumps(prompt_facts, ensure_ascii=True)
    proficiency_line = ""
    if prompt_facts.get("proficiency_level"):
        proficiency_line = "- Sentence 1 must include the exact proficiency_level phrase when provided.\n"
    return (
        "TASK: USER_SUMMARY\n"
        "Write a professional user summary in exactly 3 sentences.\n"
        "Constraints:\n"
        "- 38 to 92 words.\n"
        "- Narrative prose only (no lists or bullets).\n"
        "- Mention at least one concrete stack term from top_skills/top_languages/tools when available.\n"
        f"{proficiency_line}"
        "- Use only the facts in the payload.\n"
        "- Do not mention project names, company names, or being an assistant.\n"
        "- Return only the summary text.\n\n"
        f"FACTS_JSON: {facts_json}\n\n"
        "Summary:"
    )


def _build_llama_cpp_polish_prompt(
    facts: dict[str, Any],
    draft_summary: str,
    *,
    style_variant: str = "primary",
) -> str:
    """
    Build a rewrite prompt that converts rough ML output into resume-style prose
    without introducing new facts.
    """
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    facts_json = json.dumps(prompt_facts, ensure_ascii=True)
    proficiency_line = ""
    if prompt_facts.get("proficiency_level"):
        proficiency_line = "- Sentence 1 must include the exact proficiency_level phrase when provided.\n"
    variant_line = ""
    if style_variant == "alternative":
        variant_line = (
            "- Prefer direct active voice and concrete delivery verbs.\n"
            "- Avoid vague terms like broad, primarily, or extends.\n"
        )
    return (
        "TASK: USER_SUMMARY_REWRITE\n"
        "Rewrite the draft into a professional resume summary.\n"
        f"Rewrite style variant: {style_variant}\n"
        "Hard constraints:\n"
        "- Exactly 3 sentences.\n"
        "- 38 to 92 words.\n"
        "- Narrative prose only (no lists, no bullets).\n"
        "- Keep only information supported by DRAFT_SUMMARY and FACTS_JSON.\n"
        "- Remove any prompt artifacts (e.g., QUESTION:, ANSWER:, instructions).\n"
        "- Do not mention project names, company names, or being an assistant.\n"
        "- Mention at least one concrete stack term from top_skills/top_languages/tools when available.\n"
        f"{proficiency_line}"
        f"{variant_line}"
        "- Return only the final summary text.\n\n"
        f"FACTS_JSON: {facts_json}\n\n"
        f"DRAFT_SUMMARY: {draft_summary}\n\n"
        "Summary:"
    )


def _build_llama_cpp_expand_prompt(
    facts: dict[str, Any],
    draft_summary: str,
    rejection_reason: str,
    *,
    variant: str = "baseline",
) -> str:
    """Build an expansion prompt for short/under-structured ML outputs."""
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    facts_json = json.dumps(prompt_facts, ensure_ascii=True)
    proficiency_line = ""
    if prompt_facts.get("proficiency_level"):
        proficiency_line = "- Sentence 1 must include the exact proficiency_level phrase when provided.\n"
    variant_line = ""
    if variant == "specific":
        variant_line = (
            "- Include at least one concrete delivery or outcome signal "
            "(for example: delivered, improved, automated, measurable).\n"
        )
    return (
        "TASK: USER_SUMMARY_EXPAND\n"
        "Expand and refine the draft into a professional resume summary.\n"
        "Hard constraints:\n"
        "- Exactly 3 sentences.\n"
        "- 38 to 92 words.\n"
        "- Narrative prose only (no lists, no bullets).\n"
        "- Keep only information supported by DRAFT_SUMMARY and FACTS_JSON.\n"
        "- Do not mention project names, company names, or being an assistant.\n"
        "- Mention at least one concrete stack term from top_skills/top_languages/tools when available.\n"
        f"{proficiency_line}"
        "- Include at least one concrete delivery or outcome signal (for example: delivered, improved, automated, measurable outcomes, reliability gains).\n"
        "- Remove instruction artifacts and avoid generic phrasing.\n"
        f"{variant_line}"
        "- Return only the final summary text.\n\n"
        f"REJECTION_REASON: {rejection_reason}\n"
        f"FACTS_JSON: {facts_json}\n\n"
        f"DRAFT_SUMMARY: {draft_summary}\n\n"
        f"Variant: {variant}\n\n"
        "Summary:"
    )


def _build_llama_cpp_fluency_prompt(facts: dict[str, Any], draft_summary: str) -> str:
    """Build a final-pass prompt focused on improving narrative flow."""
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    facts_json = json.dumps(prompt_facts, ensure_ascii=True)
    proficiency_line = ""
    if prompt_facts.get("proficiency_level"):
        proficiency_line = "- Sentence 1 must include the exact proficiency_level phrase when provided.\n"
    return (
        "TASK: USER_SUMMARY_FLUENCY_REWRITE\n"
        "Improve readability and sentence flow for the draft summary.\n"
        "Hard constraints:\n"
        "- Keep exactly 3 sentences.\n"
        "- Keep 38 to 92 words.\n"
        "- Narrative prose only (no lists, no bullets).\n"
        "- Keep only information supported by DRAFT_SUMMARY and FACTS_JSON.\n"
        "- Preserve backend focus when present; if you mention a secondary domain, use a clear transition phrase (e.g., also, in addition).\n"
        f"{proficiency_line}"
        "- Remove prompt artifacts and labels (e.g., Summary:, Final summary:, QUESTION:, ANSWER:).\n"
        "- Do not mention project names, company names, or being an assistant.\n"
        "- Return only the final summary text.\n\n"
        f"FACTS_JSON: {facts_json}\n\n"
        f"DRAFT_SUMMARY: {draft_summary}\n\n"
        "Summary:"
    )


def _build_llama_cpp_resume_mold_prompt(
    facts: dict[str, Any],
    draft_summary: str,
    *,
    variant: str = "primary",
) -> str:
    """Build a final-pass prompt to mold ML text into resume-style narrative."""
    prompt_facts = dict(facts)
    prompt_facts.pop("project_names", None)
    prompt_facts.pop("tags", None)
    facts_json = json.dumps(prompt_facts, ensure_ascii=True)
    proficiency_line = ""
    if prompt_facts.get("proficiency_level"):
        proficiency_line = "- Sentence 1 must include the exact proficiency_level phrase when provided.\n"

    variant_line = ""
    if variant == "structured":
        variant_line = (
            "- Sentence 1: identity and primary focus.\n"
            "- Sentence 2: concrete delivery and outcomes.\n"
            "- Sentence 3: strengths and growth direction (do not restart a new summary).\n"
        )

    return (
        "TASK: USER_SUMMARY_RESUME_MOLD\n"
        "Rewrite the draft into polished professional resume prose.\n"
        "Hard constraints:\n"
        "- Keep exactly 3 sentences.\n"
        "- Keep 38 to 92 words.\n"
        "- Narrative prose only (no lists, no bullets).\n"
        "- Keep only information supported by DRAFT_SUMMARY and FACTS_JSON.\n"
        "- Preserve one coherent narrative across all sentences.\n"
        "- Do not start sentence 3 as a second summary.\n"
        f"{proficiency_line}"
        "- Do not include labels or artifacts (Summary:, Final summary:, QUESTION:, ANSWER:).\n"
        "- Mention at least one concrete stack term from top_skills/top_languages/tools when available.\n"
        "- Do not mention project names, company names, or being an assistant.\n"
        f"{variant_line}"
        "- Return only the final summary text.\n\n"
        f"FACTS_JSON: {facts_json}\n\n"
        f"DRAFT_SUMMARY: {draft_summary}\n\n"
        f"Variant: {variant}\n\n"
        "Summary:"
    )


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
        must_mention = ", ".join([str(x) for x in facts.get("top_skills", []) + facts.get("top_languages", []) + facts.get("tools", [])][:4])
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

    cleaned = re.sub(r"^\s*(?:final\s+)?summary\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:final\s+)?summary\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("Skills:", "").replace("Tools:", "")
    cleaned = cleaned.replace("Languages:", "")
    return " ".join(cleaned.split())


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
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(lowered)}(?![A-Za-z0-9])", re.IGNORECASE)
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


def _contains_summary_artifact_marker(summary: str) -> bool:
    """Detect leaked formatting markers that should never appear in final prose."""
    return bool(re.search(r"\b(?:final\s+)?summary\s*[:\-]", summary.lower()))


def _has_incomplete_sentence_fragment(summary: str) -> bool:
    """Detect malformed fragment sentences (e.g., 'With an.')."""
    starters = {"with", "and", "or", "but", "so", "because", "while", "although"}
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
    anchors = (facts.get("top_skills", []) or []) + (facts.get("top_languages", []) or []) + (facts.get("tools", []) or [])

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
    rebuilt = ". ".join(s.strip().rstrip(".") for s in sentences if s.strip()) + "."
    rebuilt = _normalize_summary(rebuilt)
    rebuilt = _remove_invalid_sentences(rebuilt, facts.get("project_names", []))
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
        normalized = _remove_invalid_sentences(normalized, facts.get("project_names", []))
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


def _apply_resume_style_mold_if_better(
    model_path: str,
    facts: dict[str, Any],
    draft_summary: str,
    *,
    context: str,
) -> str:
    """
    Apply optional resume-style molding and keep it only when quality improves.

    This never blocks generation: if molding is unavailable/invalid/worse,
    the original candidate is preserved.
    """
    if not draft_summary:
        return draft_summary

    base = _normalize_summary(draft_summary)
    base = _remove_invalid_sentences(base, facts.get("project_names", []))
    base = _polish_summary(base)
    base = _trim_to_sentences(base, max_sentences=3)
    base = _restore_anchor_casing(base, facts)
    base = _ensure_proficiency_in_opening(base, facts)
    base = _normalize_summary(base)
    if not base:
        return draft_summary

    mold_candidates: list[str] = []
    for idx, variant in enumerate(("primary", "structured")):
        mold_raw = llama_cpp_generate_text(
            model_path=model_path,
            prompt=_build_llama_cpp_resume_mold_prompt(
                facts,
                base,
                variant=variant,
            ),
            max_retries=0,
            max_tokens=max(120, min(184, _llama_cpp_max_tokens() + 56)),
            temperature=0.0 if idx == 0 else 0.15,
            top_p=0.95,
            max_total_seconds=max(4.0, min(10.0, _llama_cpp_max_seconds() / 3.0)),
        )
        mold_text = _extract_summary_from_raw_text(mold_raw) if mold_raw else None
        if not mold_text:
            continue
        normalized = _normalize_summary(mold_text)
        normalized = _remove_invalid_sentences(normalized, facts.get("project_names", []))
        normalized = _polish_summary(normalized)
        normalized = _trim_to_sentences(normalized, max_sentences=3)
        normalized = _restore_anchor_casing(normalized, facts)
        normalized = _ensure_proficiency_in_opening(normalized, facts)
        normalized = _normalize_summary(normalized)
        if normalized:
            mold_candidates.append(normalized)

    if not mold_candidates:
        logger.info("Signature resume-style mold unavailable; keeping selected summary (%s)", context)
        return base

    best_mold = _select_best_summary_candidate([base, *mold_candidates], facts)
    if not best_mold:
        logger.info("Signature resume-style mold could not rank candidates; keeping selected summary (%s)", context)
        return base

    base_ok, _base_reason = _is_valid_summary(base, facts)
    best_ok, best_reason = _is_valid_summary(best_mold, facts)
    if not best_ok:
        logger.info(
            "Signature resume-style mold rejected invalid candidate (%s, context=%s)",
            best_reason,
            context,
        )
        return base
    if not base_ok:
        logger.info("Signature resume-style mold accepted over invalid base (context=%s)", context)
        return best_mold

    base_score = _resume_quality_score(base, facts)
    best_score = _resume_quality_score(best_mold, facts)
    if best_score > base_score:
        logger.info(
            "Signature resume-style mold accepted (context=%s, score_delta=%d)",
            context,
            best_score - base_score,
        )
        return best_mold

    logger.info(
        "Signature resume-style mold kept original summary (context=%s, score_delta=%d)",
        context,
        best_score - base_score,
    )
    return base


def _apply_fluency_polish_if_better(
    model_path: str,
    facts: dict[str, Any],
    draft_summary: str,
    *,
    context: str,
) -> str:
    """
    Apply an optional fluency rewrite and keep it only if quality improves.

    This is deliberately non-blocking: if rewrite is unavailable/invalid/worse,
    keep the original draft without introducing new rejection paths.
    """
    if not draft_summary:
        return draft_summary

    base = _normalize_summary(draft_summary)
    base = _remove_invalid_sentences(base, facts.get("project_names", []))
    base = _polish_summary(base)
    base = _trim_to_sentences(base, max_sentences=3)
    base = _restore_anchor_casing(base, facts)
    base = _ensure_proficiency_in_opening(base, facts)
    base = _normalize_summary(base)
    if not base:
        return draft_summary

    fluency_raw = llama_cpp_generate_text(
        model_path=model_path,
        prompt=_build_llama_cpp_fluency_prompt(facts, base),
        max_retries=0,
        max_tokens=max(112, min(176, _llama_cpp_max_tokens() + 48)),
        temperature=0.0,
        top_p=0.95,
        max_total_seconds=max(4.0, min(10.0, _llama_cpp_max_seconds() / 3.0)),
    )
    fluency_text = _extract_summary_from_raw_text(fluency_raw) if fluency_raw else None
    if not fluency_text:
        logger.info("Signature fluency polish unavailable; keeping selected summary (%s)", context)
        return base

    candidate = _normalize_summary(fluency_text)
    candidate = _remove_invalid_sentences(candidate, facts.get("project_names", []))
    candidate = _polish_summary(candidate)
    candidate = _trim_to_sentences(candidate, max_sentences=3)
    candidate = _restore_anchor_casing(candidate, facts)
    candidate = _ensure_proficiency_in_opening(candidate, facts)
    candidate = _normalize_summary(candidate)
    if not candidate:
        logger.info("Signature fluency polish produced empty candidate; keeping selected summary (%s)", context)
        return base

    candidate_ok, candidate_reason = _is_valid_summary(candidate, facts)
    if not candidate_ok:
        logger.info(
            "Signature fluency polish rejected invalid candidate (%s, context=%s)",
            candidate_reason,
            context,
        )
        return base

    base_score = _resume_quality_score(base, facts)
    candidate_score = _resume_quality_score(candidate, facts)
    if candidate_score > base_score:
        logger.info(
            "Signature fluency polish accepted (context=%s, score_delta=%d)",
            context,
            candidate_score - base_score,
        )
        return candidate

    logger.info(
        "Signature fluency polish kept original summary (context=%s, score_delta=%d)",
        context,
        candidate_score - base_score,
    )
    return base


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
    summary_tokens = {_normalize_token(tok) for tok in re.findall(r"[a-zA-Z0-9]+", summary)}
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

        item_tokens = {_normalize_token(tok) for tok in re.findall(r"[a-zA-Z0-9]+", item_lower)}
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
    """Recover summary text when llama-cpp output is not valid JSON."""
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
    cleaned = re.sub(r"^\s*(?:final\s+)?summary\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:final\s+)?summary\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or None


def _is_valid_summary(summary: str, facts: dict[str, Any]) -> tuple[bool, str]:
    if _is_list_like(summary):
        return False, "list_like"
    if _contains_prompt_echo(summary):
        return False, "prompt_echo"
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
        return False, "generic_resume_tone"
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
    if _contains_example_overlap(summary):
        return False, "example_overlap"
    if _has_redundant_repetition(summary):
        return False, "redundant_repetition"
    return True, "ok"


def _llama_cpp_response_valid(response: dict[str, Any], facts: dict[str, Any]) -> tuple[bool, str]:
    """Validate structured llama-cpp response payload."""
    diagnostics = _signature_diagnostics_enabled()
    if not isinstance(response, dict):
        return False, "not_object"

    summary = _extract_summary_from_payload(response)
    if not isinstance(summary, str):
        if diagnostics:
            logger.info(
                "Signature validator missing summary text (keys=%s)",
                sorted(response.keys()) if isinstance(response, dict) else [],
            )
        return False, "missing_summary"
    if diagnostics:
        logger.info(
            "Signature validator received summary candidate (chars=%d, words=%d)",
            len(summary),
            len(summary.split()),
        )
    if not summary.strip():
        if diagnostics:
            logger.info("Signature validator rejected empty summary text before repair")
        return False, "empty_summary_text"

    repaired = _repair_summary_with_grounded_fallback(summary, facts, allow_fallback=False)
    if not repaired:
        normalized = _normalize_summary(summary or "")
        normalized = _remove_invalid_sentences(normalized, facts.get("project_names", []))
        normalized = _polish_summary(normalized)
        normalized = _trim_to_sentences(normalized, max_sentences=3)
        if not normalized:
            return False, "empty_summary"
        is_ok, reason = _is_valid_summary(normalized, facts)
        return (True, "ok") if is_ok else (False, reason)
    response.clear()
    response["summary"] = repaired
    return _is_valid_summary(repaired, facts)


def _generate_signature_with_llama_cpp(facts: dict[str, Any]) -> str | None:
    """
    Generate signature summary via local llama-cpp GGUF model.
    """
    if not llama_cpp_enabled():
        return None
    if not ml_extraction_allowed():
        return None
    if os.environ.get("ARTIFACT_MINER_DISABLE_SIGNATURE_MODEL") == "1":
        return None

    model_path = _llama_cpp_model_path()
    if not model_path:
        logger.warning("llama-cpp enabled but no signature GGUF model path could be resolved")
        return None
    started_at = perf_counter()
    last_validation_reason = "no_attempt"

    def _validator(payload: dict[str, Any]) -> tuple[bool, str]:
        nonlocal last_validation_reason
        is_valid, reason = _llama_cpp_response_valid(payload, facts)
        last_validation_reason = reason
        return is_valid, reason

    response = llama_cpp_generate_json_object(
        model_path=model_path,
        prompt=_build_llama_cpp_prompt(facts),
        validator=_validator,
        max_retries=_llama_cpp_max_retries(),
        max_tokens=_llama_cpp_max_tokens(),
        temperature=0.0,
        top_p=0.95,
        max_total_seconds=_llama_cpp_max_seconds(),
    )
    summary_text = _extract_summary_from_payload(response) if isinstance(response, dict) else None

    # Recover from malformed/non-JSON outputs with one short plain-text pass.
    if not summary_text:
        recovery_max_seconds = max(4.0, min(12.0, _llama_cpp_max_seconds() / 2.0))
        raw_text = llama_cpp_generate_text(
            model_path=model_path,
            prompt=_build_llama_cpp_plain_prompt(facts),
            max_retries=0,
            max_tokens=max(72, min(140, _llama_cpp_max_tokens())),
            temperature=0.0,
            top_p=0.95,
            max_total_seconds=recovery_max_seconds,
        )
        summary_text = _extract_summary_from_raw_text(raw_text) if raw_text else None

    if summary_text:
        raw_candidate = _restore_anchor_casing(summary_text, facts)
        candidates = [raw_candidate]

        needs_polish, polish_reason = _needs_resume_style_polish(raw_candidate)
        polish_label = polish_reason if needs_polish else "resume_polish"
        polish_max_seconds = max(4.0, min(10.0, _llama_cpp_max_seconds() / 3.0))
        polish_applied = 0
        for style_variant, temperature in (("primary", 0.0), ("alternative", 0.15)):
            polished_raw = llama_cpp_generate_text(
                model_path=model_path,
                prompt=_build_llama_cpp_polish_prompt(
                    facts,
                    raw_candidate,
                    style_variant=style_variant,
                ),
                max_retries=0,
                max_tokens=max(112, min(176, _llama_cpp_max_tokens() + 48)),
                temperature=temperature,
                top_p=0.95,
                max_total_seconds=polish_max_seconds,
            )
            polished_text = _extract_summary_from_raw_text(polished_raw) if polished_raw else None
            if not polished_text:
                continue
            candidates.append(_restore_anchor_casing(polished_text, facts))
            polish_applied += 1
        if polish_applied > 0:
            logger.info(
                "Signature style polish applied via llama-cpp (%s, candidates=%d)",
                polish_label,
                polish_applied,
            )
        else:
            logger.info(
                "Signature style polish unavailable; continuing with original ML summary (%s)",
                polish_label,
            )

        summary_text = _select_best_summary_candidate(candidates, facts)
        if summary_text:
            summary_text = _apply_resume_style_mold_if_better(
                model_path,
                facts,
                summary_text,
                context="primary",
            )
            summary_text = _apply_fluency_polish_if_better(
                model_path,
                facts,
                summary_text,
                context="primary",
            )

    def _attempt_expansion_retry(draft_summary: str, rejection_reason: str) -> str | None:
        if not _should_expand_after_rejection(rejection_reason):
            return None

        expansion_candidates: list[str] = []
        expansion_max_seconds = max(4.0, min(12.0, _llama_cpp_max_seconds() / 3.0))
        for idx, variant in enumerate(("baseline", "specific")):
            expanded_raw = llama_cpp_generate_text(
                model_path=model_path,
                prompt=_build_llama_cpp_expand_prompt(
                    facts,
                    draft_summary,
                    rejection_reason,
                    variant=variant,
                ),
                max_retries=0,
                max_tokens=max(128, min(196, _llama_cpp_max_tokens() + 72)),
                temperature=0.0 if idx == 0 else 0.15,
                top_p=0.95,
                max_total_seconds=expansion_max_seconds,
            )
            expanded_text = _extract_summary_from_raw_text(expanded_raw) if expanded_raw else None
            if not expanded_text:
                continue
            expansion_candidates.append(_restore_anchor_casing(expanded_text, facts))

        if not expansion_candidates:
            logger.info(
                "Signature expansion retry unavailable; no expanded candidates (%s)",
                rejection_reason,
            )
            return None

        expanded_best = _select_best_summary_candidate([draft_summary, *expansion_candidates], facts)
        if not expanded_best:
            logger.info(
                "Signature expansion retry could not rank expanded candidates (%s)",
                rejection_reason,
            )
            return None
        expanded_best = _apply_resume_style_mold_if_better(
            model_path,
            facts,
            expanded_best,
            context="expansion",
        )
        expanded_best = _apply_fluency_polish_if_better(
            model_path,
            facts,
            expanded_best,
            context="expansion",
        )

        expanded_repaired = _repair_summary_with_grounded_fallback(
            expanded_best,
            facts,
            allow_fallback=False,
        )
        if not expanded_repaired:
            expanded_normalized = _normalize_summary(expanded_best or "")
            expanded_normalized = _remove_invalid_sentences(
                expanded_normalized,
                facts.get("project_names", []),
            )
            expanded_normalized = _polish_summary(expanded_normalized)
            expanded_normalized = _trim_to_sentences(expanded_normalized, max_sentences=3)
            expanded_reason = "empty_normalized"
            expanded_words = len(expanded_normalized.split()) if expanded_normalized else 0
            expanded_sentences = _sentence_count(expanded_normalized) if expanded_normalized else 0
            if expanded_normalized:
                expanded_reason = _is_valid_summary(expanded_normalized, facts)[1]
            logger.info(
                "Signature expansion retry rejected candidate (initial_reason=%s, expanded_reason=%s, expanded_words=%d, expanded_sentences=%d)",
                rejection_reason,
                expanded_reason,
                expanded_words,
                expanded_sentences,
            )
            return None

        expanded_ok, expanded_reason = _is_valid_summary(expanded_repaired, facts)
        if not expanded_ok:
            logger.info(
                "Signature expansion retry still invalid (%s)",
                expanded_reason,
            )
            return None

        logger.info(
            "Signature expansion retry accepted via llama-cpp (initial_reason=%s)",
            rejection_reason,
        )
        return expanded_repaired

    elapsed = perf_counter() - started_at
    if not summary_text:
        logger.warning(
            "llama-cpp signature generation failed validation/response (%s, elapsed=%.1fs)",
            last_validation_reason,
            elapsed,
        )
        return None

    repaired = _repair_summary_with_grounded_fallback(summary_text, facts, allow_fallback=False)
    if not repaired:
        normalized = _normalize_summary(summary_text or "")
        normalized = _remove_invalid_sentences(normalized, facts.get("project_names", []))
        normalized = _polish_summary(normalized)
        normalized = _trim_to_sentences(normalized, max_sentences=3)
        rejection_reason = "empty_normalized"
        if normalized:
            _ok, rejection_reason = _is_valid_summary(normalized, facts)
        expanded = _attempt_expansion_retry(summary_text, rejection_reason)
        if expanded:
            return expanded
        logger.warning(
            "llama-cpp signature generation produced invalid repaired summary (%s, elapsed=%.1fs)",
            rejection_reason,
            elapsed,
        )
        return None
    ok, reason = _is_valid_summary(repaired, facts)
    if not ok:
        expanded = _attempt_expansion_retry(repaired, reason)
        if expanded:
            return expanded
        logger.warning(
            "llama-cpp signature summary still invalid (%s, elapsed=%.1fs)",
            reason,
            elapsed,
        )
        return None
    logger.info("llama-cpp signature generation finished in %.1fs", elapsed)
    return repaired


def _has_redundant_repetition(summary: str) -> bool:
    """
    Detect substantial repetition at sentence and phrase level.

    We reject summaries that restate the same domain point with high lexical
    overlap or repeated 4-gram phrases.
    """
    sentences = _split_sentences(summary)
    if len(sentences) >= 2:
        for i in range(len(sentences)):
            left_tokens = set(_tokenize_words(sentences[i]))
            left_domains = _sentence_domains(sentences[i])
            for j in range(i + 1, len(sentences)):
                right_tokens = set(_tokenize_words(sentences[j]))
                right_domains = _sentence_domains(sentences[j])
                if not (left_domains & right_domains):
                    continue
                if _jaccard_similarity(left_tokens, right_tokens) >= 0.62:
                    return True

    tokens = _tokenize_words(summary)
    if len(tokens) < 12:
        return False

    seen_ngrams: set[tuple[str, str, str, str]] = set()
    for i in range(len(tokens) - 3):
        ngram = (tokens[i], tokens[i + 1], tokens[i + 2], tokens[i + 3])
        if ngram in seen_ngrams:
            return True
        seen_ngrams.add(ngram)

    return False


def _join_phrases(items: list[str], limit: int = 3) -> str:
    """Join short phrase lists with readable English conjunctions."""
    trimmed = [item for item in items if item][:limit]
    if not trimmed:
        return ""
    if len(trimmed) == 1:
        return trimmed[0]
    if len(trimmed) == 2:
        return f"{trimmed[0]} and {trimmed[1]}"
    return f"{', '.join(trimmed[:-1])}, and {trimmed[-1]}"


def _role_phrase(role: str | None) -> str:
    """Map internal role labels to resume-friendly identity phrases."""
    if not role:
        return "software contributor"
    lowered = role.lower()
    if "leader" in lowered:
        return "technical contributor with leadership experience"
    if "solo" in lowered:
        return "independent software contributor"
    if "core" in lowered:
        return "core engineering contributor"
    return "software contributor"


def _stage_identity_phrase(experience_stage: str | None, role: str | None) -> str:
    """Select stage-aware opening identity text for the summary."""
    stage = _normalize_stage_label(experience_stage) or (experience_stage or "").lower()
    role_phrase = _role_phrase(role)
    proficiency = _proficiency_level_from_stage(stage)

    if stage == "student":
        if proficiency:
            return f"{proficiency} Computer Science student"
        return "Data-driven Computer Science student"
    if stage == "early-career":
        if proficiency:
            return f"{proficiency} {role_phrase}"
        return f"Early-career {role_phrase}"
    if stage == "experienced":
        if proficiency:
            return f"{proficiency} software engineer"
        return "Experienced software engineer"
    return role_phrase.capitalize()


def _focus_phrase(focus: str | None) -> str:
    """Map inferred focus categories to polished narrative focus phrases."""
    focus_map = {
        "Analytics": "data and analytics delivery",
        "Backend": "backend systems and service reliability",
        "Frontend": "product interface quality and usability",
        "ML": "applied machine learning and model-driven workflows",
        "DevOps": "delivery pipelines and platform operations",
    }
    return focus_map.get(focus, "practical software development")


def _build_professional_fallback(facts: dict[str, Any]) -> str | None:
    """Deterministic summary when model output is unavailable or rejected."""
    top_skills = facts.get("top_skills", []) or []
    top_languages = facts.get("top_languages", []) or []
    tools = facts.get("tools", []) or []
    activities = facts.get("activities", []) or []
    emerging = facts.get("emerging", []) or []
    commit_focus = facts.get("commit_focus")
    cadence = facts.get("cadence")
    focus = facts.get("focus")
    role = facts.get("role")
    experience_stage = facts.get("experience_stage")

    stack_items = list(dict.fromkeys([*top_skills[:2], *top_languages[:1], *tools[:1]]))
    stack = _join_phrases(stack_items, limit=4)
    activity_phrase = _join_phrases(activities, limit=2)
    emerging_phrase = _join_phrases(emerging, limit=2)

    sentence_1 = (
        f"{_stage_identity_phrase(experience_stage, role)} focused on {_focus_phrase(focus)}."
    )

    delivery_parts: list[str] = []
    if commit_focus:
        delivery_parts.append(f"{commit_focus} delivery")
    if cadence and cadence not in {"steady", "unknown"}:
        delivery_parts.append(f"{cadence} execution patterns")
    if activity_phrase:
        delivery_parts.append(activity_phrase)
    if not delivery_parts:
        delivery_parts.append("measurable engineering outcomes")
    sentence_2 = (
        f"Recent work delivers {_join_phrases(delivery_parts, limit=2)} through reliable, outcome-oriented implementation."
    )

    if stack:
        sentence_3 = f"Core stack includes {stack}."
    else:
        sentence_3 = "Builds maintainable software with clear technical communication."

    if emerging_phrase:
        stage = (experience_stage or "").lower()
        if stage == "student":
            sentence_3 = f"{sentence_3.rstrip('.')} while building applied depth in {emerging_phrase} through portfolio work."
        elif stage == "experienced":
            sentence_3 = (
                f"{sentence_3.rstrip('.')} while continuing to expand applied depth in {emerging_phrase} "
                "with mature engineering judgment."
            )
        else:
            sentence_3 = f"{sentence_3.rstrip('.')} while currently expanding applied depth in {emerging_phrase} through portfolio work."
    else:
        sentence_3 = f"{sentence_3.rstrip('.')} Communicates technical decisions clearly to engineering and business stakeholders."

    summary = " ".join([sentence_1, sentence_2, sentence_3]).strip()
    summary = _normalize_summary(summary)
    summary = _remove_invalid_sentences(summary, facts.get("project_names", []))
    summary = _polish_summary(summary)
    summary = _trim_to_sentences(summary, max_sentences=3)
    return summary if summary else None


def _validated_fallback_summary(facts: dict[str, Any], *, context: str) -> str | None:
    """Build and validate deterministic fallback summary."""
    fallback_summary = _build_professional_fallback(facts)
    if not fallback_summary:
        logger.info("Signature fallback unavailable%s (reason=builder_returned_empty)", context)
        return None
    fallback_words = len(fallback_summary.split())
    fallback_sentences = _sentence_count(fallback_summary)
    is_ok, reason = _is_valid_summary(fallback_summary, facts)
    if not is_ok:
        logger.warning(
            "Fallback summary rejected%s (%s, words=%d, sentences=%d): %s",
            context,
            reason,
            fallback_words,
            fallback_sentences,
            fallback_summary[:200],
        )
        return None
    logger.info(
        "Fallback summary validated%s (words=%d, sentences=%d)",
        context,
        fallback_words,
        fallback_sentences,
    )
    return fallback_summary


def _repair_summary_with_grounded_fallback(
    summary: str | None,
    facts: dict[str, Any],
    *,
    allow_fallback: bool = True,
) -> str | None:
    """
    Normalize and salvage borderline ML output before final validation.

    If the output is substantially malformed (very short/list-like/anchor-missing),
    use a grounded deterministic fallback sentence set to keep output stable.
    """
    raw_summary = summary or ""
    raw_words = len(raw_summary.split())
    raw_sentences = _sentence_count(raw_summary) if raw_summary else 0
    logger.info(
        "Signature repair start (raw_words=%d, raw_sentences=%d, ml_required=%s)",
        raw_words,
        raw_sentences,
        _ml_required(),
    )

    normalized = _normalize_summary(raw_summary)
    cleaned = _remove_invalid_sentences(normalized, facts.get("project_names", []))
    polished = _polish_summary(cleaned)
    normalized = _trim_to_sentences(polished, max_sentences=3)
    normalized = _ensure_proficiency_in_opening(normalized, facts)
    normalized = _normalize_summary(normalized)
    normalized_words = len(normalized.split()) if normalized else 0
    normalized_sentences = _sentence_count(normalized) if normalized else 0
    logger.info(
        "Signature repair normalized output (words=%d, sentences=%d)",
        normalized_words,
        normalized_sentences,
    )

    # In ML-only mode (or when explicitly requested), never inject
    # deterministic template text during repair.
    if _ml_required() or not allow_fallback:
        if not normalized:
            logger.info("Signature summary rejected in ML-only repair mode (reason=empty_normalized)")
            return None
        is_ok, reason = _is_valid_summary(normalized, facts)
        if not is_ok and reason == "missing_delivery_signal":
            injected = _inject_delivery_signal(normalized, facts)
            if injected:
                injected_ok, injected_reason = _is_valid_summary(injected, facts)
                if injected_ok:
                    logger.info(
                        "Signature repair injected delivery signal and accepted ML-only summary "
                        "(words=%d, sentences=%d)",
                        len(injected.split()),
                        _sentence_count(injected),
                    )
                    return injected
                logger.info(
                    "Signature repair delivery-signal injection still invalid in ML-only mode (%s)",
                    injected_reason,
                )
        if not is_ok:
            logger.info(
                "Signature summary rejected in ML-only repair mode (reason=%s, words=%d, sentences=%d)",
                reason,
                normalized_words,
                normalized_sentences,
            )
            return None
        logger.info(
            "Signature repair accepted ML-only summary (words=%d, sentences=%d)",
            normalized_words,
            normalized_sentences,
        )
        return normalized

    if not normalized:
        logger.info("Signature repair produced empty normalized output; attempting deterministic fallback")
        return _validated_fallback_summary(facts, context=" after empty ML output")

    is_ok, reason = _is_valid_summary(normalized, facts)
    if is_ok:
        logger.info(
            "Signature repair accepted normalized ML summary (words=%d, sentences=%d)",
            normalized_words,
            normalized_sentences,
        )
        return normalized

    logger.info(
        "Signature repair validation failed before fallback (reason=%s, words=%d, sentences=%d)",
        reason,
        normalized_words,
        normalized_sentences,
    )
    fallback_summary = _validated_fallback_summary(facts, context=" after ML validation failure")
    if not fallback_summary:
        logger.warning(
            "Signature repair could not validate deterministic fallback; returning normalized ML output (reason=%s)",
            reason,
        )
        return normalized
    fallback_words = len(fallback_summary.split())
    fallback_sentences = _sentence_count(fallback_summary)

    short_or_malformed = (
        reason.startswith("word_count=")
        or reason.startswith("sentence_count=")
        or reason in {
            "list_like",
            "prompt_echo",
            "no_skill_language_tool_anchor",
            "mentions_project_name",
            "example_overlap",
            "redundant_repetition",
            "meta_summary_marker",
            "fragment_sentence",
        }
    )
    if short_or_malformed:
        logger.info(
            "Signature summary fallback engaged after ML validation failure "
            "(reason=%s, normalized_words=%d, normalized_sentences=%d, "
            "fallback_words=%d, fallback_sentences=%d)",
            reason,
            normalized_words,
            normalized_sentences,
            fallback_words,
            fallback_sentences,
        )
        return fallback_summary

    merged = f"{normalized.rstrip('.')} {fallback_summary}"
    merged = _normalize_summary(merged)
    merged = _remove_invalid_sentences(merged, facts.get("project_names", []))
    merged = _polish_summary(merged)
    merged = _trim_to_sentences(merged, max_sentences=3)
    merged_words = len(merged.split()) if merged else 0
    merged_sentences = _sentence_count(merged) if merged else 0
    merged_ok, merged_reason = _is_valid_summary(merged, facts)
    if merged_ok:
        logger.info(
            "Signature repair accepted merged summary (merged_words=%d, merged_sentences=%d)",
            merged_words,
            merged_sentences,
        )
        return merged
    logger.info(
        "Signature summary fallback engaged after merged summary validation failure "
        "(initial_reason=%s, merged_reason=%s, merged_words=%d, merged_sentences=%d)",
        reason,
        merged_reason,
        merged_words,
        merged_sentences,
    )
    return fallback_summary


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
        return _CACHE[cache_key]

    llama_cpp_summary = _generate_signature_with_llama_cpp(facts)
    if llama_cpp_summary:
        if _cache_enabled():
            _CACHE[cache_key] = llama_cpp_summary
        logger.info("Signature summary generated successfully via llama-cpp")
        return llama_cpp_summary

    if llama_cpp_enabled():
        logger.warning("llama-cpp signature generation unavailable or invalid")
        if _ml_required():
            return None
        fallback_summary = _validated_fallback_summary(facts, context="")
        if fallback_summary:
            if _cache_enabled():
                _CACHE[cache_key] = fallback_summary
            logger.info("Signature summary generated from deterministic fallback")
            return fallback_summary
        return None

    model, tokenizer = _load_model()
    if model is None or tokenizer is None:
        logger.warning("Signature summary skipped: model not available")
        if _ml_required():
            return None
        fallback_summary = _validated_fallback_summary(facts, context="")
        if fallback_summary:
            if _cache_enabled():
                _CACHE[cache_key] = fallback_summary
            logger.info("Signature summary generated from deterministic fallback")
            return fallback_summary
        return None

    prompt = _build_prompt(facts, strict=False, include_example=True)

    try:
        reason = "unknown"
        inputs = tokenizer(prompt, return_tensors="pt")
        output = model.generate(
            **inputs,
            max_new_tokens=140,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
            pad_token_id=tokenizer.eos_token_id,
        )

        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        if "Summary:" in decoded:
            decoded = decoded.split("Summary:", 1)[-1].strip()
        summary = _repair_summary_with_grounded_fallback(decoded, facts, allow_fallback=False)

        if summary:
            is_ok, reason = _is_valid_summary(summary, facts)
            if is_ok:
                if _cache_enabled():
                    _CACHE[cache_key] = summary
                logger.info("Signature summary generated successfully")
                return summary
            logger.warning("Summary rejected by validator (%s): %s", reason, summary[:200])

        # Retry once with a stricter prompt
        logger.warning("Signature summary rejected on first pass; retrying with strict prompt")
        # Retry without the example to avoid copying if overlap was detected.
        include_example = False if reason == "example_overlap" else True
        strict_prompt = _build_prompt(facts, strict=True, include_example=include_example)
        inputs = tokenizer(strict_prompt, return_tensors="pt")
        output = model.generate(
            **inputs,
            max_new_tokens=140,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
            pad_token_id=tokenizer.eos_token_id,
        )
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        if "Summary:" in decoded:
            decoded = decoded.split("Summary:", 1)[-1].strip()
        summary = _repair_summary_with_grounded_fallback(decoded, facts, allow_fallback=False)

        if summary:
            is_ok, reason = _is_valid_summary(summary, facts)
            if is_ok:
                if _cache_enabled():
                    _CACHE[cache_key] = summary
                logger.info("Signature summary generated successfully (strict pass)")
                return summary
            logger.warning("Summary rejected after strict pass (%s): %s", reason, summary[:200])
        else:
            logger.warning("Summary rejected after strict pass: empty output")
        if _ml_required():
            return None
        fallback_summary = _validated_fallback_summary(facts, context=" after ML failure")
        if fallback_summary:
            if _cache_enabled():
                _CACHE[cache_key] = fallback_summary
            logger.info("Signature summary generated from deterministic fallback after ML rejection")
            return fallback_summary
        return None
    except Exception:
        logger.exception("Signature generation failed")
        if _ml_required():
            return None
        fallback_summary = _validated_fallback_summary(facts, context=" after exception")
        if fallback_summary:
            if _cache_enabled():
                _CACHE[cache_key] = fallback_summary
            logger.info("Signature summary generated from deterministic fallback after exception")
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
