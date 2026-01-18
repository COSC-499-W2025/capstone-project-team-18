import hashlib
import os
from typing import Iterable

_CACHE: dict[str, list[str]] = {}
_KEYBERT_MODEL = None
_KEYBERT_FAILED = False

_MAX_TEXT_CHARS = 20000
_DEFAULT_TOP_N = 10


def _hash_text(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()


def _dedupe_phrases(phrases: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for phrase in phrases:
        cleaned = " ".join(phrase.split()).strip(" \t\n\r.,;:!?()[]{}<>\"'")
        if not cleaned:
            continue
        if cleaned.isdigit():
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def _extract_with_keybert(text: str, top_n: int) -> list[str]:
    global _KEYBERT_MODEL, _KEYBERT_FAILED
    if _KEYBERT_FAILED:
        return []
    try:
        from keybert import KeyBERT
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
        _KEYBERT_FAILED = True
        return []


def extract_readme_keyphrases(text: str, top_n: int = _DEFAULT_TOP_N) -> list[str]:
    if not text or not text.strip():
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
