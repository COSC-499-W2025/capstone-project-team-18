import os
import hashlib
import re
from typing import Iterable

from src.core.ML.models.model_runtime import get_zero_shot_pipeline
from src.infrastructure.log.logging import get_logger
from src.core.ML.models.readme_analysis.constants import URL_STOPWORDS
from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.core.ML.models.readme_analysis.readme_remote_client import remote_extract_themes_bulk

"""
README insights:
- Themes: extract topic terms from README text with BERTopic.
- Tone: classify README tone with a zero-shot model (BART-MNLI).
Models are loaded lazily to avoid startup cost. Preferences consent is the
primary gate; env flags provide explicit overrides.
"""

logger = get_logger(__name__)

_TONE_LABELS = ["Professional", "Educational", "Experimental"]

_ZSC_PIPELINE = None
_ZSC_FAILED = False
_TOPIC_MODEL = None
_TOPIC_FAILED = False
_EMBEDDING_MODEL = None
_EMBEDDING_FAILED = False
_TOPIC_SINGLE_CACHE: dict[int, list[str]] = {}
_TOPIC_CORPUS_CACHE: dict[int, list[list[str]]] = {}

# BERTopic is slow and noisy on tiny corpora; skip below these thresholds.
_MIN_DOCS_FOR_BERTOPIC = 6
_MIN_TOTAL_CHARS_FOR_BERTOPIC = 1500

# Generic README command words that tend to be low-signal for themes.
_GENERIC_THEME_STOPWORDS = {
    "run",
    "running",
    "install",
    "installation",
    "setup",
    "open",
    "script",
    "scripts",
    "file",
    "files",
    "example",
    "usage",
    "command",
    "commands",
    "docker",
    "make",
    "build",
    "start",
    "starting",
    "startup",
    "readme",
    "license",
    "contributing",
    "project",
    "repository",
    "repo",
    "github",
    # Common language names that show up as noisy themes.
    "python",
    "java",
    "javascript",
    "typescript",
    "c",
    "c++",
    "cpp",
    "csharp",
    "go",
    "golang",
    "rust",
    "kotlin",
    "swift",
    "php",
    "ruby",
    "r",
    "sql",
    "bash",
    "shell",
}

# Short acronyms that are still high-signal for themes.
_THEME_SHORT_ALLOWLIST = {
    "api",
    "ui",
    "ux",
    "db",
    "ml",
    "ai",
}

def _clean_theme_terms(terms: list[str]) -> list[str]:
    """Filter URL-like and low-signal tokens from theme terms."""
    cleaned: list[str] = []
    for term in terms:
        lowered = term.strip().lower()
        if not lowered:
            continue
        if lowered.isdigit():
            continue
        if lowered in URL_STOPWORDS:
            continue
        # Single-token stopword checks first to short-circuit quickly.
        if lowered in _GENERIC_THEME_STOPWORDS:
            continue
        tokens = [t for t in re.split(r"[^a-z0-9]+", lowered) if t]
        if any(token in URL_STOPWORDS for token in tokens):
            continue
        if any(token in _GENERIC_THEME_STOPWORDS for token in tokens):
            continue
        # Drop tokens with digits (often IDs or usernames).
        if any(any(ch.isdigit() for ch in token) for token in tokens):
            continue
        # Drop very short or low-signal tokens.
        if len(tokens) == 1 and len(tokens[0]) < 4 and tokens[0] not in _THEME_SHORT_ALLOWLIST:
            continue
        if len(tokens) >= 2 and all(len(t) < 4 for t in tokens):
            continue
        # Drop likely repo/user names: single token with no vowels or too long.
        if len(tokens) == 1:
            token = tokens[0]
            if len(token) > 20 or not re.search(r"[aeiou]", token):
                continue
        cleaned.append(term)
    return cleaned


def _get_classifier():
    global _ZSC_PIPELINE, _ZSC_FAILED
    """Return the cached zero-shot classifier, or None if unavailable/disabled."""
    if not ml_extraction_allowed():
        return None
    if os.environ.get("ARTIFACT_MINER_DISABLE_ZSC") == "1":
        logger.info("Zero-shot classifier disabled via ARTIFACT_MINER_DISABLE_ZSC")
        return None
    if _ZSC_FAILED:
        logger.info("Zero-shot classifier unavailable due to previous failure")
        return None
    if _ZSC_PIPELINE is None:
        try:
            model_name = os.environ.get(
                "ARTIFACT_MINER_ZSC_MODEL", "facebook/bart-large-mnli")
            _ZSC_PIPELINE = get_zero_shot_pipeline(model_name)
            if _ZSC_PIPELINE is None:
                _ZSC_FAILED = True
                return None
        except Exception:
            logger.exception("Failed to initialize zero-shot classifier")
            _ZSC_FAILED = True
            return None
    return _ZSC_PIPELINE


def _classify_labels(text: str, labels: list[str], threshold: float, max_labels: int) -> list[str]:
    """Score text against labels and return top matches above threshold."""
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
    """Return the cached BERTopic model, or None if unavailable/disabled."""
    if not ml_extraction_allowed():
        return None
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
                "ARTIFACT_MINER_TOPIC_MODEL", "all-mpnet-base-v2")
            # Use a stronger default embedding model for better topic separation.
            _TOPIC_MODEL = BERTopic(embedding_model=model_name, verbose=False)
        except Exception:
            logger.exception("Failed to initialize BERTopic model")
            _TOPIC_FAILED = True
            return None
    return _TOPIC_MODEL


def _get_embedding_model():
    global _EMBEDDING_MODEL, _EMBEDDING_FAILED
    """Return cached sentence-transformers model for small-corpus fallback."""
    if _EMBEDDING_FAILED:
        return None
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = os.environ.get(
                "ARTIFACT_MINER_TOPIC_MODEL", "all-mpnet-base-v2")
            # Keep fallback embeddings aligned with BERTopic for consistency.
            _EMBEDDING_MODEL = SentenceTransformer(model_name)
        except Exception:
            logger.exception("Failed to initialize embedding model for fallback")
            _EMBEDDING_FAILED = True
            return None
    return _EMBEDDING_MODEL


def _theme_fallback_keyphrases(texts: Iterable[str], max_themes: int) -> list[list[str]]:
    """Fallback: extract keyphrases per README when topic modeling is unsuitable."""
    from src.core.ML.models.readme_analysis.keyphrase_extraction import (
        extract_readme_keyphrases,
    )
    results: list[list[str]] = []
    for text in texts:
        if not text or not text.strip():
            results.append([])
            continue
        results.append(extract_readme_keyphrases(text, top_n=max_themes))
    return results


def _extract_themes_small_corpus(texts: list[str], max_themes: int) -> list[list[str]]:
    """Extract themes for small corpora using embeddings + clustering (no UMAP)."""
    if not texts:
        return []
    if len(texts) < 2:
        return _theme_fallback_keyphrases(texts, max_themes)

    model = _get_embedding_model()
    if model is None:
        return _theme_fallback_keyphrases(texts, max_themes)

    try:
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np

        embeddings = model.encode(texts, show_progress_bar=False)
        n_clusters = max(1, min(3, len(texts)))
        if n_clusters == 1:
            return _theme_fallback_keyphrases(texts, max_themes)

        kmeans = KMeans(n_clusters=n_clusters, n_init="auto", random_state=42)
        labels = kmeans.fit_predict(embeddings)

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=1000,
        )
        tfidf = vectorizer.fit_transform(texts)
        terms = vectorizer.get_feature_names_out()

        cluster_terms: dict[int, list[str]] = {}
        for cluster_id in range(n_clusters):
            idx = np.where(labels == cluster_id)[0]
            if idx.size == 0:
                cluster_terms[cluster_id] = []
                continue
            mean_vec = tfidf[idx].mean(axis=0)
            mean_arr = np.asarray(mean_vec).ravel()
            top_idx = mean_arr.argsort()[::-1][:max_themes]
            cluster_terms[cluster_id] = _clean_theme_terms(
                [terms[i] for i in top_idx if mean_arr[i] > 0]
            )

        return [cluster_terms.get(label, [])[:max_themes] for label in labels]
    except Exception:
        logger.exception("Small-corpus theme fallback failed")
        return _theme_fallback_keyphrases(texts, max_themes)


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
        labels = _clean_theme_terms(labels)
        _TOPIC_SINGLE_CACHE[cache_key] = labels
        return labels
    except Exception:
        logger.exception("Failed to extract BERTopic themes from README")
        return []


def _corpus_cache_key(texts: list[str]) -> int:
    """Compute a stable cache key for a corpus of README texts."""
    normalized = [" ".join(text.split()) for text in texts]
    joined = "\n".join(normalized)
    return hash(hashlib.sha256(joined.encode("utf-8", errors="ignore")).hexdigest())


def extract_readme_themes_bulk(texts: list[str], max_themes: int = 5) -> list[list[str]]:
    """Extract themes for a README corpus with BERTopic and robust fallbacks."""
    if not texts:
        return []

    remote_themes = remote_extract_themes_bulk(texts, max_themes)
    if remote_themes is not None:
        return remote_themes

    if len(texts) < 2:
        logger.info("Single README detected; using keyphrase fallback for themes")
        return _theme_fallback_keyphrases(texts, max_themes)

    if not any(text and text.strip() for text in texts):
        logger.info("Skipping BERTopic themes: all README texts are empty")
        return [[] for _ in texts]

    total_chars = sum(len(text or "") for text in texts)
    if len(texts) < _MIN_DOCS_FOR_BERTOPIC or total_chars < _MIN_TOTAL_CHARS_FOR_BERTOPIC:
        logger.info("README corpus too small for BERTopic; using small-corpus fallback")
        return _extract_themes_small_corpus(texts, max_themes)

    model = _get_topic_model()
    if model is None:
        return _extract_themes_small_corpus(texts, max_themes)

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
            labels = [term for term, _score in topic_terms][:max_themes]
            results.append(_clean_theme_terms(labels))
        _TOPIC_CORPUS_CACHE[cache_key] = results
        return results
    except Exception:
        logger.exception("Failed to extract BERTopic themes for README corpus")
        return _extract_themes_small_corpus(texts, max_themes)

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
    """Return the dominant tone label or None if unclassified."""
    if not text or not text.strip():
        logger.info("Skipping README tone classification for empty text")
        return None

    classifier = _get_classifier()
    if classifier is None:
        return None
    try:
        result = classifier(text, _TONE_LABELS, multi_label=False)
        labels = result.get("labels", [])
        return labels[0] if labels else None
    except Exception:
        logger.exception("Failed to classify README tone")
        return None
