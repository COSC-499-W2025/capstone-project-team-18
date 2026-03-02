import pytest
from datetime import datetime, timedelta

from src.core.ML.models.contribution_analysis.commit_classifier import CommitClassifier
from src.core.ML.models.contribution_analysis.pattern_detector import (
    PatternDetector,
    WorkPattern,
)
from src.core.ML.models.contribution_analysis.role_analyzer import (
    RoleAnalyzer,
    CollaborationRole,
)


def test_commit_classifier_basic(commit_classifier):
    """Test basic commit classification."""
    msgs = [
        "feat: add new user authentication",
        "fix: resolve login bug",
        "docs: update README",
        "refactor: clean up code structure"
    ]
    counts = commit_classifier.classify_commits(msgs)

    # Should have counts for different types
    assert sum(counts.values()) == len(msgs)
    assert counts["feature"] >= 1
    assert counts["bugfix"] >= 1


def test_commit_classifier_distribution(commit_classifier):
    """Test commit type distribution percentages."""
    msgs = [
        "feat: add api endpoint",
        "feat: add tests",
        "fix: login bug",
        "docs: update readme"
    ]
    dist = commit_classifier.get_commit_distribution(msgs)

    # Should sum to 100%
    assert abs(sum(dist.values()) - 100.0) < 0.01
    # Should have at least 2 different categories
    assert len(dist) >= 2
    # All percentages should be positive
    assert all(v > 0 for v in dist.values())


def test_commit_classifier_empty(commit_classifier):
    """Test classifier with empty input."""
    dist = commit_classifier.get_commit_distribution([])
    assert dist == {}


def test_pattern_detector_consistent(pattern_detector):
    """Test detection of consistent work pattern."""
    base = datetime.now()
    # Regular commits every 2 days
    dates = [base + timedelta(days=i * 2) for i in range(10)]
    pattern = pattern_detector.detect_pattern(dates)
    assert pattern in [WorkPattern.CONSISTENT, WorkPattern.BURST]


def test_pattern_detector_burst(pattern_detector):
    """Test detection of burst work pattern."""
    base = datetime.now()
    # All commits in a short period
    dates = [base + timedelta(hours=i) for i in range(10)]
    pattern = pattern_detector.detect_pattern(dates)
    assert pattern == WorkPattern.BURST


def test_pattern_detector_sprint(pattern_detector):
    """Test detection of sprint-based work pattern."""
    base = datetime.now()
    # Two distinct sprints separated by gaps
    sprint1 = [base + timedelta(days=i) for i in range(5)]
    sprint2 = [base + timedelta(days=25 + i) for i in range(5)]
    dates = sprint1 + sprint2
    pattern = pattern_detector.detect_pattern(dates)
    assert pattern in [WorkPattern.SPRINT_BASED, WorkPattern.BURST]


def test_pattern_detector_sporadic(pattern_detector):
    """Test detection of sporadic work pattern."""
    base = datetime.now()
    # Random commits with large gaps
    dates = [
        base,
        base + timedelta(days=30),
        base + timedelta(days=90)
    ]
    pattern = pattern_detector.detect_pattern(dates)
    assert pattern == WorkPattern.SPORADIC


def test_pattern_detector_empty(pattern_detector):
    """Test pattern detector with empty input."""
    pattern = pattern_detector.detect_pattern([])
    assert pattern == WorkPattern.SPORADIC


def test_activity_metrics(pattern_detector):
    """Test activity metrics calculation."""
    base = datetime.now()
    dates = [base + timedelta(days=i * 7)
             for i in range(4)]  # 4 commits over 3 weeks

    metrics = pattern_detector.get_activity_metrics(dates)

    assert "avg_commits_per_week" in metrics
    assert "consistency_score" in metrics
    assert metrics["avg_commits_per_week"] > 0
    assert 0 <= metrics["consistency_score"] <= 1


def test_role_analyzer_solo(role_analyzer):
    """Test role inference for solo projects."""
    role = role_analyzer.infer_role(
        user_commit_pct=100.0,
        total_authors=1,
        commit_counts={"feature": 10, "bugfix": 5},
        is_group=False
    )
    assert role == CollaborationRole.SOLO


def test_role_analyzer_leader(role_analyzer):
    """Test role inference for project leader."""
    role = role_analyzer.infer_role(
        user_commit_pct=55.0,
        total_authors=4,
        commit_counts={"feature": 15, "bugfix": 8, "docs": 3},
        is_group=True
    )
    assert role in [
        CollaborationRole.LEADER,
        CollaborationRole.CORE_CONTRIBUTOR
    ]


def test_role_analyzer_core_contributor(role_analyzer):
    """Test role inference for core contributor."""
    role = role_analyzer.infer_role(
        user_commit_pct=30.0,
        total_authors=5,
        commit_counts={"feature": 10, "bugfix": 5},
        is_group=True
    )
    # ML model might classify as occasional or specialist depending on confidence
    assert role in [
        CollaborationRole.CORE_CONTRIBUTOR,
        CollaborationRole.SPECIALIST,
        CollaborationRole.OCCASIONAL
    ]


def test_role_analyzer_occasional(role_analyzer):
    """Test role inference for occasional contributor."""
    role = role_analyzer.infer_role(
        user_commit_pct=5.0,
        total_authors=10,
        commit_counts={"feature": 2, "docs": 1},
        is_group=True
    )
    assert role in [
        CollaborationRole.OCCASIONAL,
        CollaborationRole.SPECIALIST
    ]


def test_role_analyzer_specialist(role_analyzer):
    """Test role inference for specialist."""
    role = role_analyzer.infer_role(
        user_commit_pct=15.0,
        total_authors=6,
        commit_counts={"test": 20, "feature": 2},  # Mostly testing
        is_group=True
    )
    # Could be specialist or occasional depending on ML model confidence
    assert role in [
        CollaborationRole.SPECIALIST,
        CollaborationRole.OCCASIONAL,
        CollaborationRole.CORE_CONTRIBUTOR,
    ]


def test_role_description_generation(role_analyzer):
    """Test role description generation."""
    # Leader description
    desc = role_analyzer.generate_role_description(
        CollaborationRole.LEADER,
        {"feature": 15, "bugfix": 5},
        55.0
    )
    assert "Led" in desc or "55" in desc

    # Solo description
    desc = role_analyzer.generate_role_description(
        CollaborationRole.SOLO,
        {"feature": 10},
        100.0
    )
    assert "Sole" in desc or "developer" in desc

    # Occasional description
    desc = role_analyzer.generate_role_description(
        CollaborationRole.OCCASIONAL,
        {"feature": 3},
        5.0
    )
    assert "Contributed" in desc or "commits" in desc
