import json
import os
import hashlib
import re
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

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

_MODEL = None
_TOKENIZER = None
_MODEL_FAILED = False
_CACHE: dict[str, str] = {}


def _ml_required() -> bool:
    """
    Return whether callers explicitly require ML-generated summaries.

    When true, deterministic fallback summaries are disabled so the caller
    can enforce strict model-only behavior.
    """
    return os.environ.get("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML") == "1"


def _get_model_name() -> str:
    # If no explicit override, choose a smaller model on CPU to avoid OOM.
    override = os.environ.get("ARTIFACT_MINER_SIGNATURE_MODEL")
    if override:
        return override

    if torch.cuda.is_available():
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
        return _MODEL, _TOKENIZER
    except Exception:
        logger.exception("Failed to load signature model")
        _MODEL_FAILED = True
        return None, None


def _facts_hash(facts: dict[str, Any]) -> str:
    """Create a stable cache key for a facts payload."""
    serialized = json.dumps(facts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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
    cleaned = cleaned.replace("Skills:", "").replace("Tools:", "")
    cleaned = cleaned.replace("Languages:", "")
    return " ".join(cleaned.split())


def _is_list_like(text: str) -> bool:
    """Heuristic: detect bullet/list style outputs instead of narrative prose."""
    lowered = text.lower()
    if "skills:" in lowered or "tools:" in lowered or "languages:" in lowered:
        return True
    if "\n-" in text or "\n•" in text:
        return True
    return False


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
        if any(bad in lowered for bad in SUMMARY_BANNED_PHRASES):
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
    for item in items:
        if not item:
            continue
        item_lower = item.lower()
        if item_lower in lowered:
            return True
        if _normalize_token(item) and _normalize_token(item) in normalized_summary:
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
    """Return true if summary leaks a project name from the input facts."""
    lowered = summary.lower()
    for name in project_names:
        if name and name.lower() in lowered:
            return True
    return False


def _is_valid_summary(summary: str, facts: dict[str, Any]) -> tuple[bool, str]:
    if _is_list_like(summary):
        return False, "list_like"
    word_count = len(summary.split())
    if word_count < 30 or word_count > 140:
        return False, f"word_count={word_count}"
    sentence_count = summary.count(".")
    if not (2 <= sentence_count <= 6):
        return False, f"sentence_count={sentence_count}"

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
    stage = (experience_stage or "").lower()
    role_phrase = _role_phrase(role)

    if stage == "student":
        return "Data-driven Computer Science student"
    if stage == "early-career":
        return f"Early-career {role_phrase}"
    if stage == "experienced":
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
        f"{_stage_identity_phrase(experience_stage, role)} with applied experience in {_focus_phrase(focus)}."
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
        f"Recent work reflects {_join_phrases(delivery_parts, limit=2)}, with emphasis on clear, outcome-oriented implementation."
    )

    if stack:
        sentence_3 = (
            f"Strong in {stack}, with a proven ability to explain complex results clearly for both engineering and business audiences."
        )
    else:
        sentence_3 = (
            "Builds maintainable solutions and explains technical decisions clearly for both engineering and business audiences."
        )

    sentences = [sentence_1, sentence_2, sentence_3]
    if emerging_phrase:
        stage = (experience_stage or "").lower()
        if stage == "student":
            sentences.append(
                f"Curious learner with growing exposure to {emerging_phrase} through portfolio projects."
            )
        elif stage == "experienced":
            sentences.append(
                f"Brings mature technical judgment while continuing to expand applied depth in {emerging_phrase}."
            )
        else:
            sentences.append(
                f"Currently expanding applied experience in {emerging_phrase} through portfolio projects."
            )

    summary = " ".join(sentences[:4]).strip()
    summary = _normalize_summary(summary)
    summary = _remove_invalid_sentences(summary, facts.get("project_names", []))
    summary = _polish_summary(summary)
    summary = _trim_to_sentences(summary, max_sentences=6)
    return summary if summary else None


def generate_signature(facts: dict[str, Any]) -> str | None:
    """
    Generate a dynamic developer signature using a local LLM.
    Returns None if ML is disabled or model fails.
    """
    if not facts:
        return None

    cache_key = _facts_hash(facts)
    if cache_key in _CACHE:
        logger.info("Signature summary cache hit")
        return _CACHE[cache_key]

    model, tokenizer = _load_model()
    if model is None or tokenizer is None:
        logger.warning("Signature summary skipped: model not available")
        if _ml_required():
            return None
        fallback_summary = _build_professional_fallback(facts)
        if not fallback_summary:
            return None
        is_ok, reason = _is_valid_summary(fallback_summary, facts)
        if is_ok:
            _CACHE[cache_key] = fallback_summary
            logger.info("Signature summary generated from deterministic fallback")
            return fallback_summary
        logger.warning("Fallback summary rejected (%s): %s", reason, fallback_summary[:200])
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
        summary = _normalize_summary(decoded)
        summary = _remove_invalid_sentences(summary, facts.get("project_names", []))
        summary = _polish_summary(summary)
        summary = _trim_to_sentences(summary, max_sentences=6)

        if summary:
            is_ok, reason = _is_valid_summary(summary, facts)
            if is_ok:
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
        summary = _normalize_summary(decoded)
        summary = _remove_invalid_sentences(summary, facts.get("project_names", []))
        summary = _polish_summary(summary)
        summary = _trim_to_sentences(summary, max_sentences=6)

        if summary:
            is_ok, reason = _is_valid_summary(summary, facts)
            if is_ok:
                _CACHE[cache_key] = summary
                logger.info("Signature summary generated successfully (strict pass)")
                return summary
            logger.warning("Summary rejected after strict pass (%s): %s", reason, summary[:200])
        else:
            logger.warning("Summary rejected after strict pass: empty output")
        if _ml_required():
            return None
        fallback_summary = _build_professional_fallback(facts)
        if not fallback_summary:
            return None
        is_ok, reason = _is_valid_summary(fallback_summary, facts)
        if is_ok:
            _CACHE[cache_key] = fallback_summary
            logger.info("Signature summary generated from deterministic fallback after ML rejection")
            return fallback_summary
        logger.warning("Fallback summary rejected after ML failure (%s): %s", reason, fallback_summary[:200])
        return None
    except Exception:
        logger.exception("Signature generation failed")
        if _ml_required():
            return None
        fallback_summary = _build_professional_fallback(facts)
        if not fallback_summary:
            return None
        is_ok, reason = _is_valid_summary(fallback_summary, facts)
        if is_ok:
            _CACHE[cache_key] = fallback_summary
            logger.info("Signature summary generated from deterministic fallback after exception")
            return fallback_summary
        logger.warning("Fallback summary rejected after exception (%s): %s", reason, fallback_summary[:200])
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
        "experience_stage": experience_stage,
    }
    return facts
