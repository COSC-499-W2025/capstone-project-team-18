import os
from src.core.ML.models.model_runtime import get_zero_shot_pipeline
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


def _batch_size() -> int:
    """Read commit classification batch size from env with a safe default."""
    raw = os.environ.get("ARTIFACT_MINER_COMMIT_CLASSIFIER_BATCH_SIZE", "16")
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 16


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
            _CLASSIFIER_PIPELINE = get_zero_shot_pipeline(model_name)
            if _CLASSIFIER_PIPELINE is None:
                _CLASSIFIER_FAILED = True
                return None
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

        prepared_messages: list[str] = []
        for msg in messages:
            if not msg or not msg.strip():
                counts["unknown"] += 1
                continue

            first_line = msg.split('\n')[0].strip()[:_MAX_COMMIT_MESSAGE_LENGTH]
            if not first_line:
                counts["unknown"] += 1
                continue
            prepared_messages.append(first_line)

        if not prepared_messages:
            return counts

        size = _batch_size()
        for start in range(0, len(prepared_messages), size):
            batch = prepared_messages[start:start + size]
            try:
                results = self.model(
                    batch,
                    _COMMIT_LABELS,
                    multi_label=False,
                    batch_size=size,
                )
                if isinstance(results, dict):
                    results = [results]

                if len(results) != len(batch):
                    raise ValueError(
                        f"Unexpected result size: got {len(results)}, expected {len(batch)}"
                    )

                for result in results:
                    self._apply_ml_result(counts, result)
            except Exception as e:
                logger.warning(f"Failed to classify commit batch: {e}")
                fallback = self._fallback_classify(batch)
                for key, value in fallback.items():
                    counts[key] += value

        return counts

    def _apply_ml_result(self, counts: dict[str, int], result: dict) -> None:
        """
        Update output counts from a single zero-shot inference result payload.
        """
        labels = result.get("labels") or []
        scores = result.get("scores") or []
        if not labels or not scores:
            counts["unknown"] += 1
            return

        top_label = labels[0]
        top_score = scores[0]
        if top_score < _MIN_CONFIDENCE_THRESHOLD:
            counts["unknown"] += 1
            return

        category = _LABEL_MAP.get(top_label, "unknown")
        counts[category] += 1

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
