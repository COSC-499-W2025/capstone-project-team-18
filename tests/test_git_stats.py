import shutil
import tempfile
from git import Repo
from pathlib import Path
import zipfile
import pytest

from classes.report import ProjectReport
from classes.statistic import ProjectStatCollection
from src.classes.analyzer import extract_file_reports
from src.utils.project_discovery import ProjectFiles


@pytest.fixture
def unequal_contribution_dir(tmp_path: Path) -> Path:
    """Creates a directory with project having unequal contributions (Bob: 2 commits, Charlie: 1)."""
    team_dir = tmp_path / "UnequalProject"
    team_dir.mkdir()
    repo = Repo.init(team_dir)

    # Bob makes 2 commits (66.67%)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Bob")
        config.set_value("user", "email", "bob@example.com")
    (team_dir / "file1.py").write_text("# First feature")
    repo.index.add(["file1.py"])
    repo.index.commit("Bob's first commit")
    (team_dir / "file2.py").write_text("# Second feature")
    repo.index.add(["file2.py"])
    repo.index.commit("Bob's second commit")

    # Charlie makes 1 commit (33.33%)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Charlie")
        config.set_value("user", "email", "charlie@example.com")
    (team_dir / "file3.py").write_text("# Charlie's feature")
    repo.index.add(["file3.py"])
    repo.index.commit("Charlie's commit")

    # Return the parent temp directory which contains the project folder
    return tmp_path


@pytest.fixture
def git_dir(tmp_path: Path) -> Path:
    """Creates directory with individual project (1 author) and group project (2 authors)."""
    # Individual project with single author
    solo_dir = tmp_path / "SoloProject"
    solo_dir.mkdir()
    repo1 = Repo.init(solo_dir)
    with repo1.config_writer() as config:
        config.set_value("user", "name", "Alice")
        config.set_value("user", "email", "alice@example.com")
    (solo_dir / "solo_work.py").write_text("# Solo project")
    repo1.index.add(["solo_work.py"])
    repo1.index.commit("Initial solo commit")

    # Group project with multiple authors
    team_dir = tmp_path / "TeamProject"
    team_dir.mkdir()
    repo2 = Repo.init(team_dir)
    with repo2.config_writer() as config:
        config.set_value("user", "name", "Bob")
        config.set_value("user", "email", "bob@example.com")
    (team_dir / "feature1.py").write_text("# Feature by Bob")
    repo2.index.add(["feature1.py"])
    repo2.index.commit("Add feature 1")
    with repo2.config_writer() as config:
        config.set_value("user", "name", "Charlie")
        config.set_value("user", "email", "charlie@example.com")
    (team_dir / "feature2.py").write_text("# Feature by Charlie")
    repo2.index.add(["feature2.py"])
    repo2.index.commit("Add feature 2")

    return tmp_path


@pytest.fixture
def empty_repo_dir(tmp_path: Path) -> Path:
    """Creates directory with initialized Git repository but no commits."""
    project_dir = tmp_path / "EmptyRepo"
    project_dir.mkdir()
    Repo.init(project_dir)

    return tmp_path


@pytest.fixture
def corrupted_file(tmp_path: Path) -> Path:
    """Creates an invalid file (not a directory) to simulate corrupted input."""
    bad_file = tmp_path / "corrupted.file"
    bad_file.write_text("This is not a project directory")
    return bad_file


def test_git_authorship_single_author(git_dir: Path):
    """Test Git authorship analysis with single author"""
    solo_report = ProjectReport(project_path=str(
        git_dir / "SoloProject"), project_name="SoloProject", project_repo=Repo(str(git_dir / "SoloProject")), user_email="charlie@example.com")

    is_group = solo_report.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    total_authors = solo_report.get_value(
        ProjectStatCollection.TOTAL_AUTHORS.value)
    authors_per_file = solo_report.get_value(
        ProjectStatCollection.AUTHORS_PER_FILE.value)

    # Single author = individual project
    assert is_group is False
    assert total_authors == 1
    assert isinstance(authors_per_file, dict)
    assert authors_per_file.get("solo_work.py") == 1


def test_git_authorship_multiple_authors(git_dir: Path):
    """Test Git authorship analysis with multiple authors"""
    team_report = ProjectReport(project_path=str(
        git_dir / "TeamProject"), project_name="TeamProject", project_repo=Repo(str(git_dir / "TeamProject")), user_email="charlie@example.com")

    is_group = team_report.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    total_authors = team_report.get_value(
        ProjectStatCollection.TOTAL_AUTHORS.value)
    authors_per_file = team_report.get_value(
        ProjectStatCollection.AUTHORS_PER_FILE.value)

    # Multiple authors = group project
    assert is_group is True
    assert total_authors == 2
    assert isinstance(authors_per_file, dict)
    assert "feature1.py" in authors_per_file
    assert "feature2.py" in authors_per_file


def test_git_authorship_user_commit_percentage():
    """Test calculation of user's commit percentage in group projects"""
    # Create zip with unequal contribution (Bob: 2 commits, Charlie: 1 commit)
    temp_dir = tempfile.mkdtemp()
    try:
        team_dir = Path(temp_dir) / "UnequalProject"
        team_dir.mkdir()
        repo = Repo.init(team_dir)

        # Bob makes 2 commits (66.67%)
        with repo.config_writer() as config:
            config.set_value("user", "name", "Bob")
            config.set_value("user", "email", "bob@example.com")
        (team_dir / "file1.py").write_text("# First feature")
        repo.index.add(["file1.py"])
        repo.index.commit("Bob's first commit")
        (team_dir / "file2.py").write_text("# Second feature")
        repo.index.add(["file2.py"])
        repo.index.commit("Bob's second commit")

        # Charlie makes 1 commit (33.33%)
        with repo.config_writer() as config:
            config.set_value("user", "name", "Charlie")
            config.set_value("user", "email", "charlie@example.com")
        (team_dir / "file3.py").write_text("# Charlie's feature")
        repo.index.add(["file3.py"])
        repo.index.commit("Charlie's commit")

        # Test with Bob's email (project already unzipped into temp_dir)
        report_bob = ProjectReport(
            project_path=str(temp_dir + "/UnequalProject"),
            project_name="UnequalProject",
            user_email="bob@example.com",
            project_repo=repo
        )
        bob_percentage = report_bob.get_value(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value
        )
        assert bob_percentage is not None
        assert pytest.approx(bob_percentage, 0.01) == 66.67

        # Test with Charlie's email
        report_charlie = ProjectReport(
            project_path=str(temp_dir + "/UnequalProject"),
            project_name="UnequalProject",
            user_email="charlie@example.com",
            project_repo=repo
        )
        charlie_percentage = report_charlie.get_value(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value
        )
        assert charlie_percentage is not None
        assert pytest.approx(charlie_percentage, 0.01) == 33.33

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_authorship_no_user_email_provided(git_dir):
    """Test that user commit percentage is None when no email provided"""
    team_report = ProjectReport(
        project_path=str(git_dir / "TeamProject"),
        project_name="TeamProject",
        user_email=None,
        project_repo=Repo(str(git_dir / "TeamProject"))
    )

    # Should have Git stats but no user commit percentage
    is_group = team_report.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    user_percentage = team_report.get_value(
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value
    )

    assert is_group is True
    assert user_percentage is None


def test_git_authorship_single_author_no_percentage(git_dir):
    """Test that single-author projects don't calculate user percentage"""
    solo_report = ProjectReport(
        project_path=str(git_dir / "SoloProject"),
        project_name="SoloProject",
        user_email="alice@example.com",
        project_repo=Repo(str(git_dir / "SoloProject"))
    )

    # Even with email provided, single-author projects shouldn't have percentage
    is_group = solo_report.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    user_percentage = solo_report.get_value(
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value
    )

    assert is_group is False
    assert user_percentage is None


def test_git_authorship_user_not_in_project(git_dir):
    """Test user commit percentage when user email not found in project"""
    team_report = ProjectReport(
        project_path=str(git_dir / "TeamProject"),
        project_name="TeamProject",
        user_email="nonexistent@example.com",
        project_repo=Repo(str(git_dir / "TeamProject"))
    )

    # Should calculate 0% for non-contributing user
    user_percentage = team_report.get_value(
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value
    )
    assert user_percentage is not None
    assert user_percentage == 0.0


def test_git_authorship_nonexistent_project_name(git_dir):
    """Test handling of project name not in zip file"""
    report = ProjectReport(
        project_path=str(git_dir),
        project_name="NonexistentProject"
    )

    # Should return None for all Git-related stats
    is_group = report.get_value(ProjectStatCollection.IS_GROUP_PROJECT.value)
    total_authors = report.get_value(ProjectStatCollection.TOTAL_AUTHORS.value)
    authors_per_file = report.get_value(
        ProjectStatCollection.AUTHORS_PER_FILE.value)

    assert is_group is None
    assert total_authors is None
    assert authors_per_file is None


def test_git_authorship_corrupted_zip(corrupted_file: Path):
    """Test handling of corrupted/invalid zip file"""
    # Pass a path that exists but is not a project directory
    report = ProjectReport(
        project_path=str(corrupted_file),
        project_name="AnyProject"
    )

    # Should handle invalid input gracefully
    is_group = report.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    assert is_group is None


def test_git_authorship_no_git_repository():
    """Test handling of project without .git directory"""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create project structure without initializing Git
        project_dir = Path(temp_dir) / "NoGitProject"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("print('No git')")
        (project_dir / "utils.py").write_text("# Utils")

        report = ProjectReport(
            project_path=str(temp_dir),
            project_name="NoGitProject"
        )

        # Should return None for all Git stats
        is_group = report.get_value(
            ProjectStatCollection.IS_GROUP_PROJECT.value)
        total_authors = report.get_value(
            ProjectStatCollection.TOTAL_AUTHORS.value)

        assert is_group is None
        assert total_authors is None

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_authorship_multiple_files_single_author(git_dir):
    """Test authors_per_file with multiple files but single author"""
    solo_report = ProjectReport(
        project_path=str(git_dir / "SoloProject"),
        project_name="SoloProject",
        project_repo=Repo(str(git_dir / "SoloProject")),
        user_email="charlie@example.com"
    )

    authors_per_file = solo_report.get_value(
        ProjectStatCollection.AUTHORS_PER_FILE.value
    )

    # All files should have exactly 1 author
    assert isinstance(authors_per_file, dict)
    for filename, author_count in authors_per_file.items():
        assert author_count == 1


def test_git_authorship_file_with_multiple_contributors():
    """Test file modified by multiple authors"""
    temp_dir = tempfile.mkdtemp()
    try:
        project_dir = Path(temp_dir) / "SharedFile"
        project_dir.mkdir()
        repo = Repo.init(project_dir)

        # Alice creates file
        with repo.config_writer() as config:
            config.set_value("user", "name", "Alice")
            config.set_value("user", "email", "alice@example.com")
        (project_dir / "shared.py").write_text("# Initial version")
        repo.index.add(["shared.py"])
        repo.index.commit("Alice's initial commit")

        # Bob modifies same file
        with repo.config_writer() as config:
            config.set_value("user", "name", "Bob")
            config.set_value("user", "email", "bob@example.com")
        (project_dir / "shared.py").write_text("# Modified by Bob")
        repo.index.add(["shared.py"])
        repo.index.commit("Bob's modification")

        # Charlie also modifies it
        with repo.config_writer() as config:
            config.set_value("user", "name", "Charlie")
            config.set_value("user", "email", "charlie@example.com")
        (project_dir / "shared.py").write_text("# Modified by Charlie")
        repo.index.add(["shared.py"])
        repo.index.commit("Charlie's modification")

        report = ProjectReport(project_path=str(temp_dir + "/SharedFile"),
                               project_name="SharedFile",
                               project_repo=repo,
                               user_email="charlie@example.com")

        authors_per_file = report.get_value(
            ProjectStatCollection.AUTHORS_PER_FILE.value
        )
        total_authors = report.get_value(
            ProjectStatCollection.TOTAL_AUTHORS.value)

        # Should detect 3 authors total
        assert total_authors == 3
        # The shared file should have 3 authors
        assert authors_per_file.get("shared.py") == 3

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_authorship_empty_repository():
    """Test handling of Git repository with no commits"""
    temp_dir = tempfile.mkdtemp()
    try:
        project_dir = Path(temp_dir) / "EmptyRepo"
        project_dir.mkdir()
        Repo.init(project_dir)  # Initialize but make no commits

        report = ProjectReport(project_path=str(project_dir),
                               project_name="EmptyRepo")

        total_authors = report.get_value(
            ProjectStatCollection.TOTAL_AUTHORS.value)
        is_group = report.get_value(
            ProjectStatCollection.IS_GROUP_PROJECT.value)

        # Empty repo should have 0 authors
        assert total_authors is None
        assert is_group is None  # 0 authors = not a group

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_authorship_percentage_rounding():
    """Test that user commit percentage is properly rounded to 2 decimal places"""
    temp_dir = tempfile.mkdtemp()
    try:
        project_dir = Path(temp_dir) / "RoundingProject"
        project_dir.mkdir()
        repo = Repo.init(project_dir)

        # Create scenario with non-round percentage (1 out of 3 = 33.333...)
        with repo.config_writer() as config:
            config.set_value("user", "name", "Alice")
            config.set_value("user", "email", "alice@example.com")
        (project_dir / "file1.py").write_text("# Alice")
        repo.index.add(["file1.py"])
        repo.index.commit("Alice commit")

        with repo.config_writer() as config:
            config.set_value("user", "name", "Bob")
            config.set_value("user", "email", "bob@example.com")
        (project_dir / "file2.py").write_text("# Bob 1")
        repo.index.add(["file2.py"])
        repo.index.commit("Bob commit 1")
        (project_dir / "file3.py").write_text("# Bob 2")
        repo.index.add(["file3.py"])
        repo.index.commit("Bob commit 2")

        report = ProjectReport(
            project_path=str(project_dir),
            project_name="RoundingProject",
            user_email="alice@example.com",
            project_repo=repo
        )

        percentage = report.get_value(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value
        )

        # Should be rounded to 2 decimal places (33.33)
        assert isinstance(percentage, (int, float))
        assert percentage == 33.33

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_authorship_false_assumptions(git_dir):
    """Test with assert False to verify wrong assumptions fail"""
    team_report = ProjectReport(
        project_path=str(git_dir / "TeamProject"),
        project_name="TeamProject",
        project_repo=Repo(str(git_dir / "TeamProject")),
        user_email="charlie@example.com"
    )

    total_authors = team_report.get_value(
        ProjectStatCollection.TOTAL_AUTHORS.value)
    is_group = team_report.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value)

    # Wrong assumptions should be false
    assert not total_authors == 1  # Not single author
    assert not is_group is False   # Is a group project
    assert not total_authors > 5   # Not more than 5 authors
    assert not total_authors < 1   # Not less than 1 author


def test_file_report_none_for_uncommitted_files_by_user(tmp_path: Path):
    """Test that FileReport is None for files a user has not committed to in a group project.    """
    from classes.report import FileReport

    temp_dir = tempfile.mkdtemp(dir=str(tmp_path))
    project_dir = Path(temp_dir) / "SelectiveProject"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    # fileA.py: John only (0% by Charlie)
    with repo.config_writer() as config:
        config.set_value("user", "name", "John")
        config.set_value("user", "email", "john@example.com")
    (project_dir / "fileA.py").write_text("# Created by John only\nprint('John')\n")
    repo.index.add(["fileA.py"])
    repo.index.commit("John creates fileA")

    # fileB.py: Charlie only (100% by Charlie)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Charlie")
        config.set_value("user", "email", "charlie@example.com")
    (project_dir / "fileB.py").write_text("# Created by Charlie\nprint('Charlie')\n")
    repo.index.add(["fileB.py"])
    repo.index.commit("Charlie creates fileB")

    # fileC.py: John creates, Charlie modifies (50/50 contribution)
    with repo.config_writer() as config:
        config.set_value("user", "name", "John")
        config.set_value("user", "email", "john@example.com")
    (project_dir / "fileC.py").write_text("# Initial by John\nline2\n")
    repo.index.add(["fileC.py"])
    repo.index.commit("John creates fileC")

    with repo.config_writer() as config:
        config.set_value("user", "name", "Charlie")
        config.set_value("user", "email", "charlie@example.com")
    (project_dir / "fileC.py").write_text("# Initial by John\nline2_modified_by_charlie\n")
    repo.index.add(["fileC.py"])
    repo.index.commit("Charlie modifies fileC")

    project_files = ProjectFiles(
        name="SelectiveProject",
        root_path=str(project_dir),
        file_paths=["fileA.py", "fileB.py", "fileC.py"],
        repo=repo
    )

    fr = extract_file_reports(project_files, "charlie@example.com")

    # create a project report for Charlie, should only contain files B & C
    pr = ProjectReport(file_reports=fr,
                       project_path=str(project_dir),
                       project_repo=Repo(str(project_dir)),
                       project_name="SelectiveProject",
                       user_email="charlie@example.com")

    # should only be two files in ProjectReport
    assert len(fr) == 2

    shutil.rmtree(temp_dir, ignore_errors=True)
