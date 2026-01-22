"""
This pytest file will just simply test that the app runs without errors.
More detailed tests will be in their respective modules.
"""

import pytest

from src.interface.cli.cli_service_handler import start_miner_cli
from src.core.report import ProjectReport
from src.utils.errors import NoDiscoveredProjects, ErrorCode
from src.infrastructure.database.utils.database_access import get_project_from_project_name


@pytest.fixture(autouse=True, scope="function")
def mock_engine(monkeypatch, blank_db):
    """
    Tells start_miner to use our fake_get_engine function
    rather than the real get_engine() function
    """

    def fake_get_engine():
        return blank_db

    monkeypatch.setattr(
        "src.services.mining_service.get_engine", fake_get_engine)

    yield blank_db


def test_app_runs(mock_engine):
    """
    Test that the main app function runs without errors.
    """
    # Use a sample zipped file path for testing
    sample_zipped_file = "./tests/resources/mac_projects.zip"
    sample_email = "bob@example.com"

    start_miner_cli(sample_zipped_file, sample_email)

    project_a = get_project_from_project_name(
        "ProjectA", engine=mock_engine)
    project_b = get_project_from_project_name(
        "ProjectB", engine=mock_engine)

    assert project_a is not None
    assert project_b is not None
    assert isinstance(project_a, ProjectReport)
    assert isinstance(project_b, ProjectReport)


def test_app_runs_empty_zip():
    """
    Test that the main app function raises ValueError
    for a zip file that contains one empty folder.
    """
    # Use a sample zipped file path for testing
    sample_zipped_file = "./tests/resources/empty_project.zip"
    sample_email = "bob@example.com"

    with pytest.raises(NoDiscoveredProjects):
        start_miner_cli(sample_zipped_file, sample_email)


def test_app_runs_git_repo_wrong_email():
    """
    Test that the main app function raises ValueError
    for a zip file that contains a git project with
    the wrong email.
    """
    # Use a sample zipped file path for testing
    sample_zipped_file = "./tests/resources/sample_git_project_one_author.zip"
    sample_email = "spencer@example.com"

    miner_results = start_miner_cli(sample_zipped_file, sample_email)

    assert miner_results.success == False
    assert len(miner_results.project_errors) != 0
    assert miner_results.project_errors[0].error_code == ErrorCode.NO_RELEVANT_FILES.value
