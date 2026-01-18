import os

_TONE_LABELS = ["Professional", "Educational", "Experimental"]

_ZSC_PIPELINE = None
_ZSC_FAILED = False
_TOPIC_MODEL = None
_TOPIC_FAILED = False
_TOPIC_CACHE: dict[int, list[str]] = {}


def _get_classifier():
    global _ZSC_PIPELINE, _ZSC_FAILED
    if _ZSC_FAILED or os.environ.get("ARTIFACT_MINER_DISABLE_ZSC") == "1":
        return None
    if _ZSC_PIPELINE is None:
        try:
            from transformers import pipeline
            model_name = os.environ.get(
                "ARTIFACT_MINER_ZSC_MODEL", "facebook/bart-large-mnli")
            _ZSC_PIPELINE = pipeline(
                "zero-shot-classification", model=model_name)
        except Exception:
            _ZSC_FAILED = True
            return None
    return _ZSC_PIPELINE


def _classify_labels(text: str, labels: list[str], threshold: float, max_labels: int) -> list[str]:
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
    if _TOPIC_FAILED or os.environ.get("ARTIFACT_MINER_DISABLE_BERTOPIC") == "1":
        return None
    if _TOPIC_MODEL is None:
        try:
            from bertopic import BERTopic
            model_name = os.environ.get(
                "ARTIFACT_MINER_TOPIC_MODEL", "all-MiniLM-L6-v2")
            _TOPIC_MODEL = BERTopic(embedding_model=model_name, verbose=False)
        except Exception:
            _TOPIC_FAILED = True
            return None
    return _TOPIC_MODEL


def _extract_topics(text: str, max_topics: int) -> list[str]:
    model = _get_topic_model()
    if model is None:
        return []
    cache_key = hash(text)
    cached = _TOPIC_CACHE.get(cache_key)
    if cached is not None:
        return cached[:max_topics]
    topics, _ = model.fit_transform([text])
    topic_id = topics[0]
    if topic_id == -1:
        return []
    topic_terms = model.get_topic(topic_id) or []
    labels = [term for term, _score in topic_terms][:max_topics]
    _TOPIC_CACHE[cache_key] = labels
    return labels

def extract_readme_themes(text: str, max_themes: int = 5) -> list[str]:
    if not text or not text.strip():
        return []

    return _extract_topics(text, max_themes)


def classify_readme_tone(text: str) -> str | None:
    if not text or not text.strip():
        return None

    labels = _classify_labels(text, _TONE_LABELS, threshold=0.35, max_labels=1)
    return labels[0] if labels else None
