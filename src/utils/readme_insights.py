import re

_THEME_KEYWORDS: dict[str, set[str]] = {
    "User Authentication": {"authentication", "auth", "login", "jwt", "oauth", "rbac", "session"},
    "Real-Time Data Processing": {"real-time", "realtime", "streaming", "kafka", "websocket", "pub/sub",
                                  "event-driven", "event streaming"},
    "API Development": {"api", "rest", "graphql", "endpoint", "microservice"},
    "Data Analytics": {"analytics", "dashboard", "visualization", "etl", "pipeline"},
    "Machine Learning": {"machine learning", "ml", "model", "training", "inference", "classification"},
}

_TONE_KEYWORDS: dict[str, set[str]] = {
    "Professional": {"production", "enterprise", "scalable", "performance", "security",
                     "robust", "deployment", "maintainable"},
    "Educational": {"tutorial", "learning", "course", "assignment", "homework", "lab",
                    "example", "guide"},
    "Experimental": {"prototype", "poc", "experiment", "research", "hack", "sandbox",
                     "proof of concept"},
}


def _score_keywords(text: str, keywords: set[str]) -> int:
    hits = 0
    for keyword in keywords:
        escaped = re.escape(keyword)
        if re.fullmatch(r"[a-z0-9]+", keyword) and len(keyword) <= 4:
            pattern = rf"\b{escaped}\b"
        else:
            pattern = escaped
        hits += len(re.findall(pattern, text))
    return hits


def _ranked_labels(text: str, mapping: dict[str, set[str]]) -> list[tuple[str, int]]:
    scores: dict[str, int] = {}
    for label, keywords in mapping.items():
        score = _score_keywords(text, keywords)
        if score > 0:
            scores[label] = score
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def extract_readme_themes(text: str, max_themes: int = 5) -> list[str]:
    if not text or not text.strip():
        return []

    normalized = text.lower()
    ranked = _ranked_labels(normalized, _THEME_KEYWORDS)
    if not ranked:
        return []

    return [name for name, _score in ranked[:max_themes]]


def classify_readme_tone(text: str) -> str | None:
    if not text or not text.strip():
        return None

    normalized = text.lower()
    ranked = _ranked_labels(normalized, _TONE_KEYWORDS)
    if not ranked:
        return None

    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None

    return ranked[0][0]
