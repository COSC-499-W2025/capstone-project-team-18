import hashlib
import os
from typing import Iterable
import re

from keybert import KeyBERT
from src.infrastructure.log.logging import get_logger
from src.core.ML.models.readme_analysis.constants import URL_STOPWORDS
from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed

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
        # Normalize punctuation and whitespace to improve de-duping.
        cleaned = " ".join(phrase.split()).strip(" \t\n\r.,;:!?()[]{}<>\"'")
        if not cleaned:
            continue
        if cleaned.isdigit():
            continue
        lowered = cleaned.lower()
        if lowered in URL_STOPWORDS:
            continue
        tokens = [t for t in re.split(r"[^a-z0-9]+", lowered) if t]
        if any(token in URL_STOPWORDS for token in tokens):
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
    if not ml_extraction_allowed():
        return []
    if os.environ.get("ARTIFACT_MINER_DISABLE_KEYBERT") == "1":
        logger.info("KeyBERT extraction disabled via ARTIFACT_MINER_DISABLE_KEYBERT")
        return []
    if _KEYBERT_FAILED:
        logger.info("Skipping KeyBERT extraction due to previous failure")
        return []
    try:
        model_name = os.environ.get(
            "ARTIFACT_MINER_KEYBERT_MODEL", "all-mpnet-base-v2")
        # Use the same stronger default embedding model as BERTopic.
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
