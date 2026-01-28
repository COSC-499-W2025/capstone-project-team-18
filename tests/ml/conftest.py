import pytest
import os
from datetime import datetime

from src.core.ML.models.contribution_analysis.commit_classifier import CommitClassifier
from src.core.ML.models.contribution_analysis.pattern_detector import (
    PatternDetector,
)
from src.core.ML.models.contribution_analysis.role_analyzer import (
    RoleAnalyzer,
)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_ML_TESTS") == "1":
        return  # run everything

    skip_ml = pytest.mark.skip(reason="ML tests disabled (set RUN_ML_TESTS=1)")
    for item in items:
        # Only skip tests in tests/ml
        if "tests/ml" in str(item.fspath):
            item.add_marker(skip_ml)


@pytest.fixture
def commit_classifier():
    return CommitClassifier()


@pytest.fixture
def pattern_detector():
    return PatternDetector()


@pytest.fixture
def role_analyzer():
    return RoleAnalyzer()


@pytest.fixture
def base_time():
    return datetime.now()


@pytest.fixture
def user_email():
    return "user@test.com"


@pytest.fixture
def contribution_patterns_calculator():
    from src.core.report.project.project_statistics import ProjectContributionPatterns
    return ProjectContributionPatterns()
