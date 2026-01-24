import pytest
from datetime import datetime, timedelta
from src.core.ML.models.contribution_analysis.CommitClassifier import CommitClassifier
from src.core.ML.models.contribution_analysis.PatternDetector import PatternDetector, WorkPattern
from src.core.ML.models.contribution_analysis.RoleAnalyzer import RoleAnalyzer, CollaborationRole


def test_commit_classifier_basic():
    """Test basic commit classification."""
    classifier = CommitClassifier()
    msgs = [
        "feat: add new user authentication",
        "fix: resolve login bug",
        "docs: update README",
        "refactor: clean up code structure"
    ]
    counts = classifier.classify_commits(msgs)

    # Should have counts for different types
    assert sum(counts.values()) == len(msgs)
    assert counts["feature"] >= 1
    assert counts["bugfix"] >= 1


def test_commit_classifier_distribution():
    """Test commit type distribution percentages."""
    classifier = CommitClassifier()
    msgs = [
        "feat: add api endpoint",
        "feat: add tests",
        "fix: login bug",
        "docs: update readme"
    ]
    dist = classifier.get_commit_distribution(msgs)

    # Should sum to 100%
    assert abs(sum(dist.values()) - 100.0) < 0.01
    # Feature should be 50%
    assert abs(dist.get("feature", 0) - 50.0) < 1.0


def test_commit_classifier_empty():
    """Test classifier with empty input."""
    classifier = CommitClassifier()
    dist = classifier.get_commit_distribution([])
    assert dist == {}


def test_pattern_detector_consistent():
    """Test detection of consistent work pattern."""
    detector = PatternDetector()
    base = datetime.now()
    # Regular commits every 2 days
    dates = [base + timedelta(days=i*2) for i in range(10)]
    pattern = detector.detect_pattern(dates)
    assert pattern in [WorkPattern.CONSISTENT, WorkPattern.BURST]


def test_pattern_detector_burst():
    """Test detection of burst work pattern."""
    detector = PatternDetector()
    base = datetime.now()
    # All commits in a short period
    dates = [base + timedelta(hours=i) for i in range(10)]
    pattern = detector.detect_pattern(dates)
    assert pattern == WorkPattern.BURST


def test_pattern_detector_sprint():
    """Test detection of sprint-based work pattern."""
    detector = PatternDetector()
    base = datetime.now()
    # Two distinct sprints separated by gaps
    sprint1 = [base + timedelta(days=i) for i in range(5)]
    sprint2 = [base + timedelta(days=25+i) for i in range(5)]
    dates = sprint1 + sprint2
    pattern = detector.detect_pattern(dates)
    assert pattern in [WorkPattern.SPRINT_BASED, WorkPattern.BURST]


def test_pattern_detector_sporadic():
    """Test detection of sporadic work pattern."""
    detector = PatternDetector()
    base = datetime.now()
    # Random commits with large gaps
    dates = [
        base,
        base + timedelta(days=30),
        base + timedelta(days=90)
    ]
    pattern = detector.detect_pattern(dates)
    assert pattern == WorkPattern.SPORADIC


def test_pattern_detector_empty():
    """Test pattern detector with empty input."""
    detector = PatternDetector()
    pattern = detector.detect_pattern([])
    assert pattern == WorkPattern.SPORADIC


def test_activity_metrics():
    """Test activity metrics calculation."""
    detector = PatternDetector()
    base = datetime.now()
    dates = [base + timedelta(days=i*7) for i in range(4)]  # 4 commits over 3 weeks

    metrics = detector.get_activity_metrics(dates)

    assert "avg_commits_per_week" in metrics
    assert "consistency_score" in metrics
    assert metrics["avg_commits_per_week"] > 0
    assert 0 <= metrics["consistency_score"] <= 1


def test_role_analyzer_solo():
    """Test role inference for solo projects."""
    analyzer = RoleAnalyzer()
    role = analyzer.infer_role(
        user_commit_pct=100.0,
        total_authors=1,
        commit_counts={"feature": 10, "bugfix": 5},
        is_group=False
    )
    assert role == CollaborationRole.SOLO


def test_role_analyzer_leader():
    """Test role inference for project leader."""
    analyzer = RoleAnalyzer()
    role = analyzer.infer_role(
        user_commit_pct=55.0,
        total_authors=4,
        commit_counts={"feature": 15, "bugfix": 8, "docs": 3},
        is_group=True
    )
    assert role in [CollaborationRole.LEADER, CollaborationRole.CORE_CONTRIBUTOR]


def test_role_analyzer_core_contributor():
    """Test role inference for core contributor."""
    analyzer = RoleAnalyzer()
    role = analyzer.infer_role(
        user_commit_pct=30.0,
        total_authors=5,
        commit_counts={"feature": 10, "bugfix": 5},
        is_group=True
    )
    assert role in [CollaborationRole.CORE_CONTRIBUTOR, CollaborationRole.SPECIALIST]


def test_role_analyzer_occasional():
    """Test role inference for occasional contributor."""
    analyzer = RoleAnalyzer()
    role = analyzer.infer_role(
        user_commit_pct=5.0,
        total_authors=10,
        commit_counts={"feature": 2, "docs": 1},
        is_group=True
    )
    assert role in [CollaborationRole.OCCASIONAL, CollaborationRole.SPECIALIST]


def test_role_analyzer_specialist():
    """Test role inference for specialist."""
    analyzer = RoleAnalyzer()
    role = analyzer.infer_role(
        user_commit_pct=15.0,
        total_authors=6,
        commit_counts={"test": 20, "feature": 2},  # Mostly testing
        is_group=True
    )
    # Could be specialist or occasional depending on ML model confidence
    assert role in [CollaborationRole.SPECIALIST, CollaborationRole.OCCASIONAL, CollaborationRole.CORE_CONTRIBUTOR]


def test_role_description_generation():
    """Test role description generation."""
    analyzer = RoleAnalyzer()

    # Leader description
    desc = analyzer.generate_role_description(
        CollaborationRole.LEADER,
        {"feature": 15, "bugfix": 5},
        55.0
    )
    assert "Led" in desc or "55" in desc

    # Solo description
    desc = analyzer.generate_role_description(
        CollaborationRole.SOLO,
        {"feature": 10},
        100.0
    )
    assert "Sole" in desc or "developer" in desc

    # Occasional description
    desc = analyzer.generate_role_description(
        CollaborationRole.OCCASIONAL,
        {"feature": 3},
        5.0
    )
    assert "Contributed" in desc or "commits" in desc