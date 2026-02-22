"""
This file will test the should_analyze_file() function
in the Analyzer class
"""

from src.core.analyzer import get_appropriate_analyzer
from src.core.project_discovery.project_discovery import ProjectLayout


def test_should_analyze_file_file_not_in_git_repo(project_no_git_dir: ProjectLayout, get_ready_specific_analyzer):
    """
    Tests to see that a file in a non-git project
    should be included
    """

    files = project_no_git_dir.file_paths

    for file in files:
        analyzer = get_ready_specific_analyzer(
            str(project_no_git_dir.root_path),
            str(file),
            repo=project_no_git_dir.repo,
            email="example@gmail.com"
        )

        assert analyzer.should_analyze_file() is True


def test_should_analyze_file_file_not_tracked_by_git(project_shared_file, get_ready_specific_analyzer):
    """
    Tests to see if a file that is not tracked
    in a git repo is included
    """
    not_tracked_file = "not_tracked.py"

    # Make file in project
    project_dir = project_shared_file.root_path
    project_dir.joinpath(not_tracked_file).write_text(
        "# this file is untracked\n")

    analyzer = get_ready_specific_analyzer(
        str(project_shared_file.root_path),
        not_tracked_file,
        repo=project_shared_file.repo,
        email="example@gmail.com",
    )

    # File does not exist in the repo -> not tracked -> should be included
    assert analyzer.should_analyze_file() is True


def test_should_not_include_file_not_commited_by_user(project_shared_file, get_ready_specific_analyzer):
    """
    If the user has never commited to that git
    file, check to see that the file should NOT
    be included
    """

    analyzer = get_ready_specific_analyzer(
        str(project_shared_file.root_path),
        str(project_shared_file.file_paths[0]),
        repo=project_shared_file.repo,
        email="temp@example.com",
    )

    # temp@example.com did not commit to shared.py -> should NOT be included
    assert analyzer.should_analyze_file() is False


def test_should_analyze_file_file_commited_by_user(project_shared_file, get_ready_specific_analyzer):
    """
    If a user HAS commited to a file, check to
    see the file HAS be included.
    """

    analyzer = get_ready_specific_analyzer(
        str(project_shared_file.root_path),
        str(project_shared_file.file_paths[0]),
        repo=project_shared_file.repo,
        email="alice@example.com",
    )

    # Alice committed to shared.py -> should be included
    assert analyzer.should_analyze_file() is True


def test_should_analyze_file_file_if_email_not_configured(project_shared_file, get_ready_specific_analyzer):
    """
    If the email is not configured, check to see
    that all files are included
    """

    analyzer = get_ready_specific_analyzer(
        str(project_shared_file.root_path),
        str(project_shared_file.file_paths[0]),
        repo=project_shared_file.repo,
        email=None,
    )

    # If no email is configured the analyzer should include the file
    assert analyzer.should_analyze_file() is True
