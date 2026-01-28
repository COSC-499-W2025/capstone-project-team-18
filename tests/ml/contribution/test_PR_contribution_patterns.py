"""
Integration tests for ML-based contribution pattern analysis in ProjectReport.
"""
import pytest
from datetime import timedelta

from src.core.statistic import ProjectStatCollection

def make_report(repo, email, stats=None):
    return _MockReport(repo, email, stats)


class _Author:
    """Mock commit author."""
    def __init__(self, email):
        self.email = email


class _Commit:
    """Mock git commit."""
    def __init__(self, email, message, timestamp):
        self.author = _Author(email)
        self.message = message
        self.authored_date = timestamp


class _Repo:
    """Mock git repository."""
    def __init__(self, commits):
        self.commits = commits

    def iter_commits(self):
        return iter(self.commits)


class _MockReport:
    """Mock ProjectReport for testing."""
    def __init__(self, repo, email, mock_stats=None):
        self.project_repo = repo
        self.email = email
        self.project_name = "test_project"
        self.project_statistics = []
        self._mock_stats = mock_stats or {}

    def get_value(self, key):
        return self._mock_stats.get(key)

def make_report(repo, email, stats=None):
    return _MockReport(repo, email, stats)

def test_contribution_patterns_with_ml_classifier(
    base_time,
    user_email,
    contribution_patterns_calculator,
):
    """Test that ML classifier properly categorizes commits."""
    commits = [
        _Commit(user_email, "feat: add new feature", base_time.timestamp()),
        _Commit(user_email, "fix: resolve bug", (base_time + timedelta(days=1)).timestamp()),
        _Commit(user_email, "docs: update README", (base_time + timedelta(days=2)).timestamp()),
        _Commit("other@test.com", "feat: other feature", (base_time + timedelta(days=3)).timestamp()),
    ]

    repo = _Repo(commits)
    report = make_report(
        repo,
        user_email,
        {
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 75.0,
            ProjectStatCollection.TOTAL_AUTHORS.value: 2,
            ProjectStatCollection.IS_GROUP_PROJECT.value: True,
        },
    )

    stats = contribution_patterns_calculator.calculate(report)

    # Should create 5 statistics
    assert len(stats) == 5

    commit_dist = next(
        s for s in stats if s.get_template().name == "COMMIT_TYPE_DISTRIBUTION"
    )
    assert commit_dist is not None
    assert isinstance(commit_dist.value, dict)
    assert sum(commit_dist.value.values()) == pytest.approx(100.0, abs=0.1)


def test_contribution_patterns_work_pattern_detection(
    base_time,
    user_email,
    contribution_patterns_calculator,
):
    """Test ML-based work pattern detection."""
    commits = [
        _Commit(user_email, f"commit {i}", (base_time + timedelta(hours=i)).timestamp())
        for i in range(10)
    ]

    repo = _Repo(commits)
    report = make_report(
        repo,
        user_email,
        {
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 100.0,
            ProjectStatCollection.TOTAL_AUTHORS.value: 1,
            ProjectStatCollection.IS_GROUP_PROJECT.value: False,
        },
    )

    stats = contribution_patterns_calculator.calculate(report)

    work_pattern = next(
        s for s in stats if s.get_template().name == "WORK_PATTERN"
    )
    assert work_pattern is not None
    assert work_pattern.value in [
        "burst",
        "consistent",
        "sprint_based",
        "sporadic",
    ]


def test_contribution_patterns_role_inference(
    base_time,
    user_email,
    contribution_patterns_calculator,
):
    """Test ML-based collaboration role inference."""
    commits = [
        _Commit(user_email, "feat: feature 1", base_time.timestamp()),
        _Commit(user_email, "feat: feature 2", (base_time + timedelta(days=1)).timestamp()),
        _Commit("other1@test.com", "fix: bug", (base_time + timedelta(days=2)).timestamp()),
        _Commit("other2@test.com", "docs: docs", (base_time + timedelta(days=3)).timestamp()),
    ]

    repo = _Repo(commits)
    report = make_report(
        repo,
        user_email,
        {
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 50.0,
            ProjectStatCollection.TOTAL_AUTHORS.value: 3,
            ProjectStatCollection.IS_GROUP_PROJECT.value: True,
        },
    )

    stats = contribution_patterns_calculator.calculate(report)

    role = next(
        s for s in stats if s.get_template().name == "COLLABORATION_ROLE"
    )
    assert role is not None
    assert role.value in [
        "leader",
        "core_contributor",
        "specialist",
        "occasional",
        "solo",
    ]


def test_contribution_patterns_no_repo(contribution_patterns_calculator, user_email):
    """Test that calculator handles missing repo gracefully."""
    report = make_report(None, user_email)
    stats = contribution_patterns_calculator.calculate(report)
    assert stats == []


def test_contribution_patterns_no_commits(
    base_time,
    user_email,
    contribution_patterns_calculator,
):
    """Test that calculator handles no user commits gracefully."""
    commits = [
        _Commit("other@test.com", "feat: feature", base_time.timestamp()),
    ]

    repo = _Repo(commits)
    report = make_report(repo, user_email)
    stats = contribution_patterns_calculator.calculate(report)
    assert stats == []


def test_contribution_patterns_activity_metrics(
    base_time,
    user_email,
    contribution_patterns_calculator,
):
    """Test activity metrics calculation."""
    commits = [
        _Commit(user_email, f"commit {i}", (base_time + timedelta(weeks=i)).timestamp())
        for i in range(4)
    ]

    repo = _Repo(commits)
    report = make_report(
        repo,
        user_email,
        {
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 100.0,
            ProjectStatCollection.TOTAL_AUTHORS.value: 1,
            ProjectStatCollection.IS_GROUP_PROJECT.value: False,
        },
    )

    stats = contribution_patterns_calculator.calculate(report)

    metrics = next(
        s for s in stats if s.get_template().name == "ACTIVITY_METRICS"
    )
    assert metrics is not None
    assert "avg_commits_per_week" in metrics.value
    assert "consistency_score" in metrics.value
    assert metrics.value["avg_commits_per_week"] > 0
