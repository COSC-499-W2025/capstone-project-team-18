"""
This file will test the should_include() function
in the Analyzer class
"""

from src.classes.analyzer import get_appropriate_analyzer
from pathlib import Path
from src.utils.project_discovery.project_discovery import ProjectFiles


def test_should_include_file_not_in_git_repo(project_no_git_dir: ProjectFiles):
    """
    Tests to see that a file in a non-git project
    should be included
    """

    files = project_no_git_dir.file_paths

    for file in files:
        analyzer = get_appropriate_analyzer(
            path_to_top_level_project=project_no_git_dir.root_path,
            relative_path=file,
            repo=project_no_git_dir.repo,
            email="example@gmail.com"
        )

        assert analyzer.should_include() is True


def test_should_include_file_not_tracked_by_git(project_shared_file):
    """
    Tests to see if a file that is not tracked
    in a git repo is included
    """
    not_tracked_file = "not_tracked.py"

    # Make file in project
    project_dir = Path(project_shared_file.root_path)
    project_dir.joinpath(not_tracked_file).write_text(
        "# this file is untracked\n")

    analyzer = get_appropriate_analyzer(
        path_to_top_level_project=project_shared_file.root_path,
        relative_path=not_tracked_file,
        repo=project_shared_file.repo,
        email="example@gmail.com",
    )

    # File does not exist in the repo -> not tracked -> should be included
    assert analyzer.should_include() is True


def test_should_not_include_file_not_commited_by_user(project_shared_file):
    """
    If the user has never commited to that git
    file, check to see that the file should NOT
    be included
    """

    analyzer = get_appropriate_analyzer(
        path_to_top_level_project=project_shared_file.root_path,
        relative_path=project_shared_file.file_paths[0],
        repo=project_shared_file.repo,
        email="temp@example.com",
    )

    # temp@example.com did not commit to shared.py -> should NOT be included
    assert analyzer.should_include() is False


def test_should_include_file_commited_by_user(project_shared_file):
    """
    If a user HAS commited to a file, check to
    see the file HAS be included.
    """

    analyzer = get_appropriate_analyzer(
        path_to_top_level_project=project_shared_file.root_path,
        relative_path=project_shared_file.file_paths[0],
        repo=project_shared_file.repo,
        email="alice@example.com",
    )

    # Alice committed to shared.py -> should be included
    assert analyzer.should_include() is True


def test_should_include_file_if_email_not_configured(project_shared_file):
    """
    If the email is not configured, check to see
    that all files are included
    """

    analyzer = get_appropriate_analyzer(
        path_to_top_level_project=project_shared_file.root_path,
        relative_path=project_shared_file.file_paths[0],
        repo=project_shared_file.repo,
        email=None,
    )

    # If no email is configured the analyzer should include the file
    assert analyzer.should_include() is True
