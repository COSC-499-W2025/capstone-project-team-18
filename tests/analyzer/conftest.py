from pathlib import Path
import pytest

from src.core.analyzer import get_appropriate_analyzer, BaseFileAnalyzer
from src.core.project_discovery.project_discovery import ProjectLayout
from src.database.api.models import UserConfigModel


@pytest.fixture
def project_context_from_root():
    """
    Builds a ProjectLayout using the passed root path
    """

    def _create(root_path) -> ProjectLayout:

        return ProjectLayout(
            file_paths=[],
            root_path=Path(root_path),
            name="test_project",
            repo=None
        )

    return _create


@pytest.fixture
def get_ready_specific_analyzer(project_context_from_root):
    def _create(root_path, rel_path) -> BaseFileAnalyzer:
        return get_appropriate_analyzer(
            UserConfigModel(), project_context_from_root(root_path), rel_path)
