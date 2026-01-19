import os
import hashlib

from src.utils.log.logging import get_logger

"""
README insights:
- Themes: extract topic terms from README text with BERTopic.
- Tone: classify README tone with a zero-shot model (BART-MNLI).
Models are loaded lazily to avoid startup cost and can be disabled with env flags.
"""

logger = get_logger(__name__)

_TONE_LABELS = ["Professional", "Educational", "Experimental"]

_ZSC_PIPELINE = None
_ZSC_FAILED = False
_TOPIC_MODEL = None
_TOPIC_FAILED = False
_TOPIC_SINGLE_CACHE: dict[int, list[str]] = {}
_TOPIC_CORPUS_CACHE: dict[int, list[list[str]]] = {}


def _get_classifier():
    global _ZSC_PIPELINE, _ZSC_FAILED
    """Return the cached zero-shot classifier (BART-MNLI).
    Returns None if disabled by env or if initialization failed.
    """
    if os.environ.get("ARTIFACT_MINER_DISABLE_ZSC") == "1":
        logger.info("Zero-shot classifier disabled via ARTIFACT_MINER_DISABLE_ZSC")
        return None
    if _ZSC_FAILED:
        logger.info("Zero-shot classifier unavailable due to previous failure")
        return None
    if _ZSC_PIPELINE is None:
        try:
            from transformers import pipeline
            model_name = os.environ.get(
                "ARTIFACT_MINER_ZSC_MODEL", "facebook/bart-large-mnli")
            _ZSC_PIPELINE = pipeline(
                "zero-shot-classification", model=model_name)
        except Exception:
            logger.exception("Failed to initialize zero-shot classifier")
            _ZSC_FAILED = True
            return None
    return _ZSC_PIPELINE


def _classify_labels(text: str, labels: list[str], threshold: float, max_labels: int) -> list[str]:
    """Score the text against candidate labels and return the top matches.
    Uses a threshold to filter weak labels.
    """
    classifier = _get_classifier()
    if classifier is None:
        return []
    result = classifier(text, labels, multi_label=True)
    ranked = [
        label for label, score in zip(result["labels"], result["scores"])
        if score >= threshold
    ]
    return ranked[:max_labels]

def _get_topic_model():
    global _TOPIC_MODEL, _TOPIC_FAILED
    """Return the cached BERTopic model used for topic terms.
    Returns None if disabled by env or if initialization failed.
    """
    if os.environ.get("ARTIFACT_MINER_DISABLE_BERTOPIC") == "1":
        logger.info("BERTopic disabled via ARTIFACT_MINER_DISABLE_BERTOPIC")
        return None
    if _TOPIC_FAILED:
        logger.info("BERTopic unavailable due to previous failure")
        return None
    if _TOPIC_MODEL is None:
        try:
            from bertopic import BERTopic
            model_name = os.environ.get(
                "ARTIFACT_MINER_TOPIC_MODEL", "all-MiniLM-L6-v2")
            _TOPIC_MODEL = BERTopic(embedding_model=model_name, verbose=False)
        except Exception:
            logger.exception("Failed to initialize BERTopic model")
            _TOPIC_FAILED = True
            return None
    return _TOPIC_MODEL


def _extract_topics(text: str, max_topics: int) -> list[str]:
    """Extract top topic terms from BERTopic for a single README.
    Uses an in-memory cache to avoid recomputing for the same text.
    """
    model = _get_topic_model()
    if model is None:
        return []
    cache_key = hash(text)
    cached = _TOPIC_SINGLE_CACHE.get(cache_key)
    if cached is not None:
        return cached[:max_topics]
    try:
        topics, _ = model.fit_transform([text])
        topic_id = topics[0]
        if topic_id == -1:
            return []
        topic_terms = model.get_topic(topic_id) or []
        labels = [term for term, _score in topic_terms][:max_topics]
        _TOPIC_SINGLE_CACHE[cache_key] = labels
        return labels
    except Exception:
        logger.exception("Failed to extract BERTopic themes from README")
        return []


def _corpus_cache_key(texts: list[str]) -> int:
    normalized = [" ".join(text.split()) for text in texts]
    joined = "\n".join(normalized)
    return hash(hashlib.sha256(joined.encode("utf-8", errors="ignore")).hexdigest())


def extract_readme_themes_bulk(texts: list[str], max_themes: int = 5) -> list[list[str]]:
    """
    Extract topic terms for a corpus of README texts with BERTopic.
    Returns a list of theme lists aligned with the input order.
    """
    if not texts:
        return []

    if len(texts) < 2:
        logger.info("Single README detected; using keyphrase fallback for themes")
        results: list[list[str]] = []
        for text in texts:
            if not text or not text.strip():
                results.append([])
                continue
            from src.ML.models.readme_analysis.keyphrase_extraction import (
                extract_readme_keyphrases,
            )
            themes = extract_readme_keyphrases(text, top_n=max_themes)
            results.append(themes)
        return results

    if not any(text and text.strip() for text in texts):
        logger.info("Skipping BERTopic themes: all README texts are empty")
        return [[] for _ in texts]

    model = _get_topic_model()
    if model is None:
        return [[] for _ in texts]

    cache_key = _corpus_cache_key(texts)
    cached = _TOPIC_CORPUS_CACHE.get(cache_key)
    if cached is not None:
        return [themes[:max_themes] for themes in cached]

    try:
        topics, _ = model.fit_transform(texts)
        results: list[list[str]] = []
        for topic_id in topics:
            if topic_id == -1:
                results.append([])
                continue
            topic_terms = model.get_topic(topic_id) or []
            results.append([term for term, _score in topic_terms][:max_themes])
        _TOPIC_CORPUS_CACHE[cache_key] = results
        return results
    except Exception:
        logger.exception("Failed to extract BERTopic themes for README corpus")
        return [[] for _ in texts]

def extract_readme_themes(text: str, max_themes: int = 5) -> list[str]:
    """Return README theme terms inferred by BERTopic.
    Returns an empty list if no topics can be inferred.
    """
    if not text or not text.strip():
        logger.info("Skipping README theme extraction for empty text")
        return []

    themes_by_doc = extract_readme_themes_bulk([text], max_themes)
    return themes_by_doc[0] if themes_by_doc else []


def classify_readme_tone(text: str) -> str | None:
    """Return the dominant tone label or None if unclassified.
    Uses the same zero-shot classifier as theme detection.
    """
    if not text or not text.strip():
        logger.info("Skipping README tone classification for empty text")
        return None

    labels = _classify_labels(text, _TONE_LABELS, threshold=0.35, max_labels=1)
    return labels[0] if labels else None
