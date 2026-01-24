"""
Detects work patterns from commit history over time.
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics


class WorkPattern(Enum):
    """Types of work patterns based on commit frequency."""
    CONSISTENT = "consistent"
    SPRINT_BASED = "sprint_based"
    BURST = "burst"
    SPORADIC = "sporadic"
    UNKNOWN = "unknown"


class PatternDetector:
    """
    Analyzes commit timestamps to detect work patterns.
    """

    def __init__(self, sprint_window_days: int = 14):
        """
        Initialize pattern detector.

        Args:
            sprint_window_days: Number of days to consider a sprint window
        """
        self.sprint_window_days = sprint_window_days

    def detect_pattern(self, commit_dates: List[datetime]) -> WorkPattern:
        """
        Detect the work pattern from commit dates.

        Args:
            commit_dates: List of commit timestamps

        Returns:
            WorkPattern: The detected pattern
        """
        if not commit_dates or len(commit_dates) < 3:
            return WorkPattern.UNKNOWN

        # Sort dates
        sorted_dates = sorted(commit_dates)

        # Calculate intervals between commits (in days)
        intervals = []
        for i in range(1, len(sorted_dates)):
            delta = (sorted_dates[i] - sorted_dates[i-1]).days
            intervals.append(delta)

        if not intervals:
            return WorkPattern.UNKNOWN

        # Calculate statistics
        avg_interval = statistics.mean(intervals)
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
        max_interval = max(intervals)

        # Coefficient of variation
        cv = (std_interval / avg_interval) if avg_interval > 0 else 0

        # Pattern detection logic
        # Consistent: low variation, regular intervals
        if cv < 0.5 and avg_interval < 7:
            return WorkPattern.CONSISTENT

        # Sprint-based: clusters of activity with gaps
        if self._has_sprint_pattern(sorted_dates):
            return WorkPattern.SPRINT_BASED

        # Burst: many commits in short period then long gap
        if max_interval > 30 and cv > 1.5:
            return WorkPattern.BURST

        # Sporadic: irregular intervals
        if cv > 1.0:
            return WorkPattern.SPORADIC

        return WorkPattern.CONSISTENT

    def _has_sprint_pattern(self, sorted_dates: List[datetime]) -> bool:
        """
        Check if commits follow a sprint-based pattern.

        Args:
            sorted_dates: Sorted list of commit dates

        Returns:
            bool: True if sprint pattern detected
        """
        if len(sorted_dates) < 5:
            return False

        # Group commits into time windows
        windows = []
        current_window = [sorted_dates[0]]

        for i in range(1, len(sorted_dates)):
            delta = (sorted_dates[i] - current_window[0]).days
            if delta <= self.sprint_window_days:
                current_window.append(sorted_dates[i])
            else:
                if len(current_window) >= 3:
                    windows.append(current_window)
                current_window = [sorted_dates[i]]

        if len(current_window) >= 3:
            windows.append(current_window)

        # Sprint pattern: at least 2 windows with gaps between them
        return len(windows) >= 2

    def get_activity_metrics(self, commit_dates: List[datetime]) -> Dict[str, float]:
        """
        Calculate various activity metrics.

        Args:
            commit_dates: List of commit timestamps

        Returns:
            Dictionary of metrics
        """
        if not commit_dates:
            return {}

        sorted_dates = sorted(commit_dates)

        # Calculate intervals
        intervals = []
        for i in range(1, len(sorted_dates)):
            delta = (sorted_dates[i] - sorted_dates[i-1]).days
            intervals.append(delta)

        metrics = {
            'total_commits': len(commit_dates),
            'avg_commits_per_week': 0.0,
            'longest_gap_days': 0,
            'consistency_score': 0.0
        }

        if len(sorted_dates) >= 2:
            total_days = (sorted_dates[-1] - sorted_dates[0]).days
            if total_days > 0:
                metrics['avg_commits_per_week'] = (len(commit_dates) / total_days) * 7

        if intervals:
            metrics['longest_gap_days'] = max(intervals)
            # Consistency score: inverse of coefficient of variation (0-1 scale)
            avg = statistics.mean(intervals)
            std = statistics.stdev(intervals) if len(intervals) > 1 else 0
            cv = (std / avg) if avg > 0 else 0
            metrics['consistency_score'] = max(0, 1 - min(cv, 1))

        return metrics