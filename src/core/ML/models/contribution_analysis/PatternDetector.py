import os
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from sklearn.cluster import DBSCAN
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

_PATTERN_DETECTOR_DISABLED = False


class WorkPattern(Enum):
    CONSISTENT = "consistent"
    BURST = "burst"
    SPRINT_BASED = "sprint_based"
    SPORADIC = "sporadic"


class PatternDetector:
    """ML-based work pattern detector using temporal clustering."""

    def __init__(self):
        self.disabled = os.environ.get("ARTIFACT_MINER_DISABLE_PATTERN_DETECTOR") == "1"
        if self.disabled:
            logger.info("Pattern detector disabled via env variable")

    def detect_pattern(self, commit_dates: list[datetime]) -> WorkPattern:
        """Detect work pattern using DBSCAN clustering on commit timestamps."""
        if self.disabled or not commit_dates:
            return WorkPattern.SPORADIC

        if len(commit_dates) < 3:
            return WorkPattern.SPORADIC

        try:
            # Convert to timestamps (seconds since epoch)
            timestamps = np.array([dt.timestamp() for dt in commit_dates]).reshape(-1, 1)

            # Normalize to days
            timestamps_days = timestamps / (24 * 3600)

            # DBSCAN clustering: find dense commit periods
            # eps=7 days, min_samples=2 commits
            db = DBSCAN(eps=7, min_samples=2).fit(timestamps_days)
            labels = db.labels_

            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)

            # Calculate time span
            time_span = (max(commit_dates) - min(commit_dates)).days

            # Pattern detection logic based on clustering results
            if n_clusters == 0:
                # All noise ie very sporadic
                return WorkPattern.SPORADIC

            elif n_clusters == 1 and n_noise == 0:
                # Single dense cluster
                if time_span < 7:
                    return WorkPattern.BURST
                else:
                    return WorkPattern.CONSISTENT

            elif n_clusters > 1:
                # Multiple clusters
                # Check if sprint-like
                cluster_sizes = [list(labels).count(i) for i in range(n_clusters)]
                avg_cluster_size = np.mean(cluster_sizes)

                if avg_cluster_size >= 3 and time_span > 14:
                    return WorkPattern.SPRINT_BASED
                else:
                    return WorkPattern.BURST

            else:
                # Mix of clusters and noise
                if n_noise / len(labels) > 0.5:
                    return WorkPattern.SPORADIC
                else:
                    return WorkPattern.BURST

        except Exception as e:
            logger.warning(f"Failed to detect pattern with ML, using fallback: {e}")
            return self._fallback_pattern(commit_dates)

    def _fallback_pattern(self, commit_dates: list[datetime]) -> WorkPattern:
        """Fallback rule-based pattern detection."""
        if len(commit_dates) < 2:
            return WorkPattern.SPORADIC

        sorted_dates = sorted(commit_dates)
        gaps = [(sorted_dates[i+1] - sorted_dates[i]).days
                for i in range(len(sorted_dates) - 1)]

        avg_gap = np.mean(gaps)
        std_gap = np.std(gaps)

        if std_gap < 3 and avg_gap < 7:
            return WorkPattern.CONSISTENT
        elif std_gap > 10 or avg_gap > 14:
            return WorkPattern.SPORADIC
        elif max(gaps) > 21:
            return WorkPattern.SPRINT_BASED
        else:
            return WorkPattern.BURST

    def get_activity_metrics(self, commit_dates: list[datetime]) -> dict[str, float]:
        """Calculate activity metrics from commit dates."""
        if not commit_dates or len(commit_dates) < 2:
            return {
                "avg_commits_per_week": 0.0,
                "consistency_score": 0.0
            }

        sorted_dates = sorted(commit_dates)
        time_span = (sorted_dates[-1] - sorted_dates[0]).days
        weeks = max(time_span / 7, 1)

        avg_commits_per_week = len(commit_dates) / weeks

        # Consistency score based on variance in commit gaps
        gaps = [(sorted_dates[i+1] - sorted_dates[i]).days
                for i in range(len(sorted_dates) - 1)]

        if len(gaps) > 1:
            std_gap = np.std(gaps)
            # Lower std = higher consistency
            # (inverted and normalized)
            consistency_score = max(0, 1 - (std_gap / 30))
        else:
            consistency_score = 1.0

        return {
            "avg_commits_per_week": round(avg_commits_per_week, 1),
            "consistency_score": round(consistency_score, 2)
        }