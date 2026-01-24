import hashlib
import os
from typing import Iterable

from keybert import KeyBERT
from src.infrastructure.log.logging import get_logger
from src.core.ML.models.readme_analysis.constants import URL_STOPWORDS

_CACHE: dict[str, list[str]] = {}
_KEYBERT_MODEL = None
_KEYBERT_FAILED = False

_MAX_TEXT_CHARS = 20000
_DEFAULT_TOP_N = 10

logger = get_logger(__name__)


def _hash_text(text: str) -> str:
    """Normalize and hash text for cache keys."""
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()


def _dedupe_phrases(phrases: Iterable[str]) -> list[str]:
    """Clean, de-dupe, and filter noisy phrases (URLs, stopwords, numbers)."""
    seen: set[str] = set()
    deduped: list[str] = []
    for phrase in phrases:
        cleaned = " ".join(phrase.split()).strip(" \t\n\r.,;:!?()[]{}<>\"'")
        if not cleaned:
            continue
        if cleaned.isdigit():
            continue
        lowered = cleaned.lower()
        if lowered.startswith(("http://", "https://")):
            continue
        if "http" in lowered or "www." in lowered:
            continue
        if lowered in URL_STOPWORDS:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def _extract_with_keybert(text: str, top_n: int) -> list[str]:
    """Run KeyBERT extraction with lazy model init and env-based disabling."""
    global _KEYBERT_MODEL, _KEYBERT_FAILED
    if os.environ.get("ARTIFACT_MINER_DISABLE_ML") == "1" or os.environ.get(
        "ARTIFACT_MINER_DISABLE_KEYBERT"
    ) == "1":
        logger.info("KeyBERT extraction disabled via env flag")
        return []
    if _KEYBERT_FAILED:
        logger.info("Skipping KeyBERT extraction due to previous failure")
        return []
    try:
        model_name = os.environ.get(
            "ARTIFACT_MINER_KEYBERT_MODEL", "all-MiniLM-L6-v2")
        if _KEYBERT_MODEL is None:
            _KEYBERT_MODEL = KeyBERT(model_name)
        keywords = _KEYBERT_MODEL.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words="english",
            top_n=top_n,
        )
        return [kw for kw, _score in keywords]
    except Exception:
        logger.exception("KeyBERT extraction failed for model %s", model_name)
        _KEYBERT_FAILED = True
        return []


def extract_readme_keyphrases(text: str, top_n: int = _DEFAULT_TOP_N) -> list[str]:
    """Extract and cache README keyphrases, truncating long inputs."""
    if not text or not text.strip():
        logger.info("Skipping README keyphrase extraction for empty text")
        return []

    truncated = text[:_MAX_TEXT_CHARS]
    # Cache by normalized text hash to avoid re-running KeyBERT on the same README.
    cache_key = _hash_text(truncated)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return list(cached)

    phrases = _extract_with_keybert(truncated, top_n)

    phrases = _dedupe_phrases(phrases)[:top_n]
    if phrases:
        _CACHE[cache_key] = phrases

    return phrases
