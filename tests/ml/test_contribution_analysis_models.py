import pytest
from datetime import datetime, timedelta
from src.core.ML.models.contribution_analysis.CommitClassifier import CommitClassifier, CommitType
from src.core.ML.models.contribution_analysis.PatternDetector import PatternDetector, WorkPattern
from src.core.ML.models.contribution_analysis.RoleAnalyzer import RoleAnalyzer, CollaborationRole

def test_commit_classifier_distribution():
    classifier = CommitClassifier()
    msgs = ["feat: add api", "fix: login bug", "docs: update readme", "refactor code"]
    dist = classifier.get_commit_distribution(msgs)
    assert dist[CommitType.FEATURE.value] == 25.0
    assert dist[CommitType.BUGFIX.value] == 25.0

def test_pattern_detector_consistent():
    detector = PatternDetector()
    base = datetime.now()
    dates = [base + timedelta(days=i*2) for i in range(6)]
    assert detector.detect_pattern(dates) == WorkPattern.CONSISTENT

def test_pattern_detector_sprint():
    detector = PatternDetector()
    base = datetime.now()
    sprint1 = [base + timedelta(days=i) for i in range(5)]
    sprint2 = [base + timedelta(days=20+i) for i in range(5)]
    assert detector.detect_pattern(sprint1 + sprint2) == WorkPattern.SPRINT_BASED

def test_role_analyzer_leader():
    analyzer = RoleAnalyzer()
    role = analyzer.infer_role(
        user_commit_percentage=45.0,
        total_authors=4,
        commit_distribution={CommitType.FEATURE: 5, CommitType.BUGFIX: 3, CommitType.DOCUMENTATION: 2},
        is_group_project=True,
    )
    assert role == CollaborationRole.LEADER