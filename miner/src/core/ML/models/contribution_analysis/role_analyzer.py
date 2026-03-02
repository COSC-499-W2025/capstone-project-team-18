import os
from enum import Enum
from transformers import pipeline
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_ROLE_CLASSIFIER = None
_ROLE_CLASSIFIER_FAILED = False

_ROLE_LABELS = [
    "project leader and coordinator",
    "core contributor and maintainer",
    "specialist and expert",
    "occasional contributor",
    "solo developer"
]

_LABEL_MAP = {
    "project leader and coordinator": "leader",
    "core contributor and maintainer": "core_contributor",
    "specialist and expert": "specialist",
    "occasional contributor": "occasional",
    "solo developer": "solo"
}


class CollaborationRole(Enum):
    LEADER = "leader"
    CORE_CONTRIBUTOR = "core_contributor"
    SPECIALIST = "specialist"
    OCCASIONAL = "occasional"
    SOLO = "solo"


def _get_role_classifier():
    """Return cached zero-shot classifier for role inference."""
    global _ROLE_CLASSIFIER, _ROLE_CLASSIFIER_FAILED

    if os.environ.get("ARTIFACT_MINER_DISABLE_ROLE_CLASSIFIER") == "1":
        logger.info("Role classifier disabled via env variable")
        return None

    if _ROLE_CLASSIFIER_FAILED:
        logger.info("Role classifier unavailable due to previous failure")
        return None

    if _ROLE_CLASSIFIER is None:
        try:
            model_name = os.environ.get(
                "ARTIFACT_MINER_ROLE_CLASSIFIER_MODEL",
                "facebook/bart-large-mnli"
            )
            _ROLE_CLASSIFIER = pipeline(
                "zero-shot-classification",
                model=model_name
            )
            logger.info(f"Loaded role classifier: {model_name}")
        except Exception:
            logger.exception("Failed to initialize role classifier")
            _ROLE_CLASSIFIER_FAILED = True
            return None

    return _ROLE_CLASSIFIER


class RoleAnalyzer:
    """ML-based collaboration role analyzer using zero-shot classification."""

    def __init__(self):
        self.model = _get_role_classifier()

    def infer_role(
        self,
        user_commit_pct: float | None,
        total_authors: int,
        commit_counts: dict[str, int],
        is_group: bool
    ) -> CollaborationRole:
        """Infer collaboration role using ML classification."""

        # Handle solo projects
        if not is_group or total_authors == 1:
            return CollaborationRole.SOLO

        if user_commit_pct is None:
            return CollaborationRole.OCCASIONAL

        # Build a descriptive text for the classifier
        total_commits = sum(commit_counts.values())
        top_type = max(commit_counts.items(), key=lambda x: x[1])[0] if commit_counts else "unknown"

        description = (
            f"Made {user_commit_pct:.1f}% of commits in a team of {total_authors}. "
            f"Total {total_commits} commits, primarily {top_type} work."
        )

        if self.model is None:
            logger.warning("Role classifier unavailable, using fallback")
            return self._fallback_role(user_commit_pct, total_authors, is_group)

        try:
            result = self.model(
                description,
                _ROLE_LABELS,
                multi_label=False
            )

            top_label = result["labels"][0]
            top_score = result["scores"][0]

            if top_score < 0.3:
                return self._fallback_role(user_commit_pct, total_authors, is_group)

            role_str = _LABEL_MAP.get(top_label, "occasional")
            return CollaborationRole(role_str)

        except Exception as e:
            logger.warning(f"Failed to classify role with ML: {e}")
            return self._fallback_role(user_commit_pct, total_authors, is_group)

    def _fallback_role(
        self,
        user_commit_pct: float,
        total_authors: int,
        is_group: bool
    ) -> CollaborationRole:
        """Fallback rule-based role inference."""
        if not is_group:
            return CollaborationRole.SOLO

        if user_commit_pct >= 50:
            return CollaborationRole.LEADER
        elif user_commit_pct >= 25:
            return CollaborationRole.CORE_CONTRIBUTOR
        elif user_commit_pct >= 10:
            return CollaborationRole.SPECIALIST
        else:
            return CollaborationRole.OCCASIONAL

    def generate_role_description(
        self,
        role: CollaborationRole,
        commit_counts: dict[str, int],
        user_commit_pct: float | None
    ) -> str:
        """Generate readable role description."""
        total_commits = sum(commit_counts.values())

        if role == CollaborationRole.SOLO:
            return f"Sole developer with {total_commits} commits"
        elif role == CollaborationRole.LEADER:
            return f"Led project with {user_commit_pct:.1f}% of commits ({total_commits} total)"
        elif role == CollaborationRole.CORE_CONTRIBUTOR:
            return f"Core contributor with {user_commit_pct:.1f}% of commits ({total_commits} total)"
        elif role == CollaborationRole.SPECIALIST:
            return f"Specialized contributor with {total_commits} commits"
        else:
            return f"Contributed {total_commits} commits to the project"