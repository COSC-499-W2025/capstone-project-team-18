import os
from transformers import pipeline
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_CLASSIFIER_PIPELINE = None
_CLASSIFIER_FAILED = False

# Model configuration constants
_MAX_COMMIT_MESSAGE_LENGTH = 256  # BART model has 1024 token limit; 256 chars provides a safe margin for tokenization
_MIN_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence score to accept ML classification (0-1 scale)


# Commit type labels for zero-shot classification
_COMMIT_LABELS = [
    "feature implementation",
    "bug fix",
    "code refactoring",
    "documentation",
    "testing",
    "chore and maintenance",
    "performance optimization",
    "configuration"
]

_LABEL_MAP = {
    "feature implementation": "feature",
    "bug fix": "bugfix",
    "code refactoring": "refactor",
    "documentation": "docs",
    "testing": "test",
    "chore and maintenance": "chore",
    "performance optimization": "performance",
    "configuration": "config"
}


def _get_commit_classifier():
    """Return cached zero-shot classifier for commit messages."""
    global _CLASSIFIER_PIPELINE, _CLASSIFIER_FAILED

    if os.environ.get("ARTIFACT_MINER_DISABLE_COMMIT_CLASSIFIER") == "1":
        logger.info("Commit classifier disabled via env variable")
        return None

    if _CLASSIFIER_FAILED:
        logger.info("Commit classifier unavailable due to previous failure")
        return None

    if _CLASSIFIER_PIPELINE is None:
        try:
            model_name = os.environ.get(
                "ARTIFACT_MINER_COMMIT_CLASSIFIER_MODEL",
                "facebook/bart-large-mnli"
            )
            _CLASSIFIER_PIPELINE = pipeline(
                "zero-shot-classification",
                model=model_name
            )
            logger.info(f"Loaded commit classifier: {model_name}")
        except Exception:
            logger.exception("Failed to initialize commit classifier")
            _CLASSIFIER_FAILED = True
            return None

    return _CLASSIFIER_PIPELINE


class CommitClassifier:
    """ML-based commit message classifier using zero-shot learning."""

    def __init__(self):
        self.model = _get_commit_classifier()

    def classify_commits(self, messages: list[str]) -> dict[str, int]:
        """Classify commit messages and return counts by type."""
        if self.model is None:
            logger.warning("Commit classifier unavailable, using fallback")
            return self._fallback_classify(messages)

        counts = {
            "feature": 0,
            "bugfix": 0,
            "refactor": 0,
            "docs": 0,
            "test": 0,
            "chore": 0,
            "performance": 0,
            "config": 0,
            "unknown": 0
        }

        for msg in messages:
            if not msg or not msg.strip():
                counts["unknown"] += 1
                continue

            try:
                # Use first line of commit message, truncated to model's input limit
                # BART tokenizer can handle ~1024 tokens; 256 chars provides a safe margin for tokenization
                # and captures essential commit message as commits are typically <100 chars
                first_line = msg.split('\n')[0].strip()[:_MAX_COMMIT_MESSAGE_LENGTH]  # Truncate for model

                result = self.model(
                    first_line,
                    _COMMIT_LABELS,
                    multi_label=False
                )

                # Map label to category
                top_label = result["labels"][0]
                top_score = result["scores"][0]

                # Reject low-confidence predictions to avoid misclassification
                # Threshold of 0.3 gives a stable balance of precision vs coverage
                if top_score < _MIN_CONFIDENCE_THRESHOLD:  # Low confidence threshold hit
                    counts["unknown"] += 1
                else:
                    category = _LABEL_MAP.get(top_label, "unknown")
                    counts[category] += 1

            except Exception as e:
                logger.warning(f"Failed to classify commit: {e}")
                counts["unknown"] += 1

        return counts

    def _fallback_classify(self, messages: list[str]) -> dict[str, int]:
        """Fallback rule-based classification when ML model unavailable."""
        counts = {
            "feature": 0,
            "bugfix": 0,
            "refactor": 0,
            "docs": 0,
            "test": 0,
            "chore": 0,
            "performance": 0,
            "config": 0,
            "unknown": 0
        }

        for msg in messages:
            lower = msg.lower()
            if any(w in lower for w in ["feat", "add", "implement", "create"]):
                counts["feature"] += 1
            elif any(w in lower for w in ["fix", "bug", "issue", "resolve"]):
                counts["bugfix"] += 1
            elif any(w in lower for w in ["refactor", "clean", "restructure"]):
                counts["refactor"] += 1
            elif any(w in lower for w in ["doc", "readme", "comment"]):
                counts["docs"] += 1
            elif any(w in lower for w in ["test", "spec", "coverage"]):
                counts["test"] += 1
            elif any(w in lower for w in ["perf", "optimize", "speed"]):
                counts["performance"] += 1
            elif any(w in lower for w in ["config", "setup", "setting"]):
                counts["config"] += 1
            elif any(w in lower for w in ["chore", "update", "bump", "merge"]):
                counts["chore"] += 1
            else:
                counts["unknown"] += 1

        return counts

    def get_commit_distribution(self, messages: list[str]) -> dict[str, float]:
        """Return percentage distribution of commit types."""
        counts = self.classify_commits(messages)
        total = sum(counts.values())

        if total == 0:
            return {}

        return {
            key: (count / total) * 100
            for key, count in counts.items()
            if count > 0
        }