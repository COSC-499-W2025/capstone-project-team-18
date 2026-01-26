"""
Integration tests for ML-based contribution pattern analysis in ProjectReport.
"""
import pytest
from datetime import datetime, timedelta
from src.core.report.project.project_report import ProjectReport
from src.core.statistic import ProjectStatCollection


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


def test_contribution_patterns_with_ml_classifier():
    """Test that ML classifier properly categorizes commits."""
    from src.core.report.project.project_statistics import ProjectContributionPatterns

    base = datetime.now()
    commits = [
        _Commit("user@test.com", "feat: add new feature", base.timestamp()),
        _Commit("user@test.com", "fix: resolve bug", (base + timedelta(days=1)).timestamp()),
        _Commit("user@test.com", "docs: update README", (base + timedelta(days=2)).timestamp()),
        _Commit("other@test.com", "feat: other feature", (base + timedelta(days=3)).timestamp()),
    ]

    repo = _Repo(commits)
    report = _MockReport(repo, "user@test.com", {
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 75.0,
        ProjectStatCollection.TOTAL_AUTHORS.value: 2,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
    })

    calculator = ProjectContributionPatterns()
    stats = calculator.calculate(report)

    # Should create 5 statistics
    assert len(stats) == 5

    # Find the commit distribution stat
    commit_dist = next(s for s in stats if s.get_template().name == "COMMIT_TYPE_DISTRIBUTION")
    assert commit_dist is not None
    dist_value = commit_dist.value

    # Should have categorized commits
    assert isinstance(dist_value, dict)
    assert sum(dist_value.values()) == pytest.approx(100.0, abs=0.1)


def test_contribution_patterns_work_pattern_detection():
    """Test ML-based work pattern detection."""
    from src.core.report.project.project_statistics import ProjectContributionPatterns

    base = datetime.now()
    # Create burst pattern - many commits in short time
    commits = [
        _Commit("user@test.com", f"commit {i}", (base + timedelta(hours=i)).timestamp())
        for i in range(10)
    ]

    repo = _Repo(commits)
    report = _MockReport(repo, "user@test.com", {
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 100.0,
        ProjectStatCollection.TOTAL_AUTHORS.value: 1,
        ProjectStatCollection.IS_GROUP_PROJECT.value: False,
    })

    calculator = ProjectContributionPatterns()
    stats = calculator.calculate(report)

    # Find work pattern stat
    work_pattern = next(s for s in stats if s.get_template().name == "WORK_PATTERN")
    assert work_pattern is not None
    assert work_pattern.value in ["burst", "consistent", "sprint_based", "sporadic"]


def test_contribution_patterns_role_inference():
    """Test ML-based collaboration role inference."""
    from src.core.report.project.project_statistics import ProjectContributionPatterns

    base = datetime.now()
    commits = [
        _Commit("user@test.com", "feat: feature 1", base.timestamp()),
        _Commit("user@test.com", "feat: feature 2", (base + timedelta(days=1)).timestamp()),
        _Commit("other1@test.com", "fix: bug", (base + timedelta(days=2)).timestamp()),
        _Commit("other2@test.com", "docs: docs", (base + timedelta(days=3)).timestamp()),
    ]

    repo = _Repo(commits)
    report = _MockReport(repo, "user@test.com", {
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 50.0,
        ProjectStatCollection.TOTAL_AUTHORS.value: 3,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
    })

    calculator = ProjectContributionPatterns()
    stats = calculator.calculate(report)

    # Find role stat
    role = next(s for s in stats if s.get_template().name == "COLLABORATION_ROLE")
    assert role is not None
    assert role.value in ["leader", "core_contributor", "specialist", "occasional", "solo"]


def test_contribution_patterns_no_repo():
    """Test that calculator handles missing repo gracefully."""
    from src.core.report.project.project_statistics import ProjectContributionPatterns

    report = _MockReport(None, "user@test.com")
    calculator = ProjectContributionPatterns()
    stats = calculator.calculate(report)

    # Should return empty list
    assert stats == []


def test_contribution_patterns_no_commits():
    """Test that calculator handles no user commits gracefully."""
    from src.core.report.project.project_statistics import ProjectContributionPatterns

    base = datetime.now()
    commits = [
        _Commit("other@test.com", "feat: feature", base.timestamp()),
    ]

    repo = _Repo(commits)
    report = _MockReport(repo, "user@test.com")
    calculator = ProjectContributionPatterns()
    stats = calculator.calculate(report)

    # Should return empty list
    assert stats == []


def test_contribution_patterns_activity_metrics():
    """Test activity metrics calculation."""
    from src.core.report.project.project_statistics import ProjectContributionPatterns

    base = datetime.now()
    # Weekly commits for consistency
    commits = [
        _Commit("user@test.com", f"commit {i}", (base + timedelta(weeks=i)).timestamp())
        for i in range(4)
    ]

    repo = _Repo(commits)
    report = _MockReport(repo, "user@test.com", {
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 100.0,
        ProjectStatCollection.TOTAL_AUTHORS.value: 1,
        ProjectStatCollection.IS_GROUP_PROJECT.value: False,
    })

    calculator = ProjectContributionPatterns()
    stats = calculator.calculate(report)

    # Find activity metrics
    metrics = next(s for s in stats if s.get_template().name == "ACTIVITY_METRICS")
    assert metrics is not None
    assert "avg_commits_per_week" in metrics.value
    assert "consistency_score" in metrics.value
    assert metrics.value["avg_commits_per_week"] > 0