import json
import os
import hashlib
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_MODEL = None
_TOKENIZER = None
_MODEL_FAILED = False
_CACHE: dict[str, str] = {}


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
    serialized = json.dumps(facts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


_STYLE_EXAMPLE = (
    "Data-driven Computer Science Honours student with hands-on experience analyzing user and system data "
    "to generate insights that improve software delivery processes. Strong in Python, Java, SQL, Excel and "
    "Power BI with proven ability to automate reporting, build dashboards, and clearly communicate findings "
    "to technical and non-technical stakeholders. Curious learner with exposure to Generative AI and LLM evaluation."
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
    style_example = (
        "Example style (do NOT copy wording, only match tone and structure). "
        "Do NOT reuse any phrases from the example; avoid any 5-word sequence overlap.\n"
        f"Example: {_STYLE_EXAMPLE}"
    )

    base = (
        "Write a 2–4 sentence professional summary based ONLY on the facts below. "
        "The summary must be narrative, not a list. Avoid repeating full skill/tool lists; "
        "instead describe experience and impact. Do not invent tools, roles, or skills. "
        "Use a professional resume tone. Do NOT mention being an assistant or providing summaries. "
        "Avoid generic filler like 'team player', 'keen eye for detail', 'strong focus on quality', "
        "'committed to delivering high-quality work' or 'strive to meet deadlines'. "
        "Do NOT mention specific project names, company names, or team management."
    )
    if strict:
        must_mention = ", ".join([str(x) for x in facts.get("top_skills", []) + facts.get("top_languages", []) + facts.get("tools", [])][:4])
        base += (
            " Follow this structure strictly: "
            "Sentence 1: identity + focus. "
            "Sentence 2: experience + impact. "
            "Sentence 3: strengths (skills/tools) + communication/insights. "
            "Sentence 4 (optional): forward-looking interest ONLY if supported by facts."
            f" You MUST mention at least one of these terms verbatim: {must_mention}."
        )
    if include_example:
        return f"{base}\n{style_example}\n\nFacts (JSON): {facts_json}\n\nSummary:"
    return f"{base}\n\nFacts (JSON): {facts_json}\n\nSummary:"


def _normalize_summary(text: str) -> str:
    # Strip common list prefixes and redundant labels.
    cleaned = text.strip()
    cleaned = cleaned.replace("Skills:", "").replace("Tools:", "")
    cleaned = cleaned.replace("Languages:", "")
    return " ".join(cleaned.split())


def _is_list_like(text: str) -> bool:
    lowered = text.lower()
    if "skills:" in lowered or "tools:" in lowered or "languages:" in lowered:
        return True
    if "\n-" in text or "\n•" in text:
        return True
    return False


def _remove_invalid_sentences(text: str, project_names: list[str] | None = None) -> str:
    banned_phrases = [
        "resume assistant",
        "as an assistant",
        "i can provide",
        "i can help",
        "committed to delivering",
        "strive to meet deadlines",
        "high-quality work",
        "team player",
        "keen eye for detail",
        "strong focus on quality",
        "collaborative environment",
        "team members",
        "company",
        "organization",
        "project names",
    ]

    sentences = [s.strip() for s in text.split(".") if s.strip()]
    kept = []
    for s in sentences:
        lowered = s.lower()
        if any(bad in lowered for bad in banned_phrases):
            continue
        if project_names and _contains_project_name(s, project_names):
            continue
        kept.append(s)
    if not kept:
        return ""
    return ". ".join(kept) + "."


def _trim_to_sentences(text: str, max_sentences: int = 4) -> str:
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if not sentences:
        return text
    trimmed = ". ".join(sentences[:max_sentences])
    if text.endswith(".") or len(sentences) <= max_sentences:
        return trimmed + "."
    return trimmed + "."


def _normalize_token(token: str) -> str:
    return "".join(ch for ch in token.lower() if ch.isalnum())


def _summary_mentions_any(summary: str, items: list[str]) -> bool:
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
    example_tokens = _tokens(_STYLE_EXAMPLE)

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
    if not (2 <= sentence_count <= 4):
        return False, f"sentence_count={sentence_count}"

    project_names = facts.get("project_names", [])
    if _contains_project_name(summary, project_names):
        return False, "mentions_project_name"

    skills = facts.get("top_skills", [])
    langs = facts.get("top_languages", [])
    tools = facts.get("tools", [])
    if not _summary_mentions_any(summary, skills + langs + tools):
        return False, "no_skill_language_tool_anchor"
    if _contains_example_overlap(summary):
        return False, "example_overlap"
    return True, "ok"


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
        return None

    prompt = _build_prompt(facts, strict=False, include_example=True)

    try:
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
        summary = _trim_to_sentences(summary, max_sentences=4)

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
        summary = _trim_to_sentences(summary, max_sentences=4)

        if summary:
            is_ok, reason = _is_valid_summary(summary, facts)
            if is_ok:
                _CACHE[cache_key] = summary
                logger.info("Signature summary generated successfully (strict pass)")
                return summary
            logger.warning("Summary rejected after strict pass (%s): %s", reason, summary[:200])
        else:
            logger.warning("Summary rejected after strict pass: empty output")
        return None
    except Exception:
        logger.exception("Signature generation failed")
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
    }
    return facts
