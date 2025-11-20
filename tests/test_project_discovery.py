import sys
from pathlib import Path
import zipfile
import pytest
from git import Repo


from src.utils.project_discovery import discover_projects, ProjectFiles  # type: ignore  # noqa: E402
from src.classes.report import ProjectReport  # type: ignore  # noqa: E402
from src.classes.statistic import ProjectStatCollection  # type: ignore  # noqa: E402


@pytest.fixture
def multi_project_zip(tmp_path: Path) -> Path:
    """Creates zip with 3 projects containing nested folders."""
    zip_path = tmp_path / "StudentSubmissions.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        # Assignment1: 2 files in root
        zf.writestr("Assignment1/main.py", "print('Hello')")
        zf.writestr("Assignment1/README.md", "# Assignment 1")
        # Assignment2: 4 files with nested src/ and tests/ folders
        zf.writestr("Assignment2/src/app.py", "# Main app")
        zf.writestr("Assignment2/src/utils/helper.py", "# Helper functions")
        zf.writestr("Assignment2/tests/test_app.py", "# Tests")
        zf.writestr("Assignment2/config.json", "{}")
        # FinalProject: 3 files with src/models/ and docs/ folders
        zf.writestr("FinalProject/src/main.py", "# Entry point")
        zf.writestr("FinalProject/src/models/user.py", "# User model")
        zf.writestr("FinalProject/docs/README.md", "# Documentation")
    return zip_path


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


def test_discover_multiple_projects(multi_project_zip: Path, tmp_path: Path):
    """Verifies discovery of multiple projects with nested folder structures."""
    # Unzip to temp dir
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()
    import zipfile
    with zipfile.ZipFile(multi_project_zip, 'r') as zf:
        zf.extractall(extract_dir)
    result = discover_projects(str(extract_dir))
    # Should find all 3 projects
    project_names = {p.name for p in result}
    assert {"Assignment1", "Assignment2", "FinalProject"} <= project_names
    # Helper to get file paths for a project

    def get_files(name):
        for p in result:
            if p.name == name:
                return p.file_paths
        return []
    # Verify nested paths are preserved correctly
    assert "src/utils/helper.py" in get_files("Assignment2")
    assert "src/models/user.py" in get_files("FinalProject")
    # Verify file counts per project
    assert len(get_files("Assignment1")) == 2
    assert len(get_files("Assignment2")) == 4
    assert len(get_files("FinalProject")) == 3


def test_discover_git_projects(git_dir: Path):
    """Verifies discovery of projects with Git repositories."""
    result = discover_projects(str(git_dir))
    project_names = {p.name for p in result}
    assert {"SoloProject", "TeamProject"} <= project_names
    # Verify file counts
    for p in result:
        if p.name == "SoloProject":
            assert len(p.file_paths) == 1 and "solo_work.py" in p.file_paths
            assert p.repo is not None
        elif p.name == "TeamProject":
            assert len(p.file_paths) == 2
            assert "feature1.py" in p.file_paths
            assert "feature2.py" in p.file_paths
            assert p.repo is not None


def test_identify_project_type(git_dir: Path):
    """Verifies Git-based detection of individual vs group projects."""
    # Single author = individual (False)
    solo_report = ProjectReport(project_path=str(
        git_dir / "SoloProject"), project_name="SoloProject",
        project_repo=Repo(str(git_dir / "SoloProject")))

    assert solo_report.statistics.get(
        ProjectStatCollection.IS_GROUP_PROJECT.value).value is False

    # Multiple authors = group (True)
    team_report = ProjectReport(project_path=str(
        git_dir / "TeamProject"), project_name="TeamProject",
        project_repo=Repo(str(git_dir / "TeamProject")))
    assert team_report.statistics.get(
        ProjectStatCollection.IS_GROUP_PROJECT.value).value is True


def test_no_git_projects(tmp_path: Path):
    """Verifies handling of projects without Git repositories."""
    zip_path = tmp_path / "NoGitProject.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("BasicProject/main.py", "print('No git')")
        zf.writestr("BasicProject/utils.py", "# Utilities")
    # Unzip to temp dir
    extract_dir = tmp_path / "nogit_extracted"
    extract_dir.mkdir()
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    result = discover_projects(str(extract_dir))
    # Should find BasicProject with 2 files
    found = [p for p in result if p.name == "BasicProject"]
    assert found and len(found[0].file_paths) == 2
    # No Git repo = no statistics
    # (ProjectReport still expects zip_path, so this part is unchanged)
    report = ProjectReport(project_path=str(
        extract_dir), project_name="BasicProject")
    assert report.statistics.get(
        ProjectStatCollection.IS_GROUP_PROJECT.value) is None


def test_invalid_inputs(tmp_path: Path):
    """Verifies proper error handling for invalid directories."""
    # Nonexistent directory should raise FileNotFoundError
    from src.utils.project_discovery import discover_projects
    with pytest.raises(FileNotFoundError):
        discover_projects(str(tmp_path / "does_not_exist"))


def test_mac_zip_structure(tmp_path: Path):
    """Verifies handling of Mac-created zip files with parent folders and metadata."""
    mac_zip_path = Path(__file__).parent / "resources" / "mac_projects.zip"
    extract_dir = tmp_path / "mac_extracted"
    extract_dir.mkdir()
    import zipfile
    with zipfile.ZipFile(mac_zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    result = discover_projects(str(extract_dir))
    project_names = {p.name for p in result}
    # Should skip parent "Projects" folder and __MACOSX metadata
    assert "Projects" not in project_names
    assert "__MACOSX" not in project_names
    # Should find ProjectA and ProjectB as top-level projects
    assert "ProjectA" in project_names
    assert "ProjectB" in project_names

    def get_files(name):
        for p in result:
            if p.name == name:
                return p.file_paths
        return []
    # Verify ProjectA files (should filter out .DS_Store)
    assert "a_1.txt" in get_files("ProjectA")
    assert "a_2.txt" in get_files("ProjectA")
    assert "subfolder/a_3.txt" in get_files("ProjectA")
    assert ".DS_Store" not in get_files("ProjectA")
    assert len(get_files("ProjectA")) == 3
    # Verify ProjectB files
    assert "b_1.txt" in get_files("ProjectB")
    assert "b_2.txt" in get_files("ProjectB")
    assert "b_3.txt" in get_files("ProjectB")
    assert len(get_files("ProjectB")) == 3


def test_project_report_git_analysis(git_dir: Path):
    """Verifies ProjectReport correctly analyzes Git authorship statistics."""
    # Test individual project (1 author)
    solo_report = ProjectReport(project_path=str(
        git_dir / "SoloProject"), project_name="SoloProject", project_repo=Repo(str(git_dir / "SoloProject")))

    is_group = solo_report.statistics.get(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    total_authors = solo_report.statistics.get(
        ProjectStatCollection.TOTAL_AUTHORS.value)
    authors_per_file = solo_report.statistics.get(
        ProjectStatCollection.AUTHORS_PER_FILE.value)

    assert is_group is not None and is_group.value is False  # Individual project
    assert total_authors is not None and total_authors.value == 1
    assert authors_per_file is not None and isinstance(
        authors_per_file.value, dict)
    assert "solo_work.py" in authors_per_file.value
    assert authors_per_file.value["solo_work.py"] == 1

    # Test group project (2 authors)
    team_report = ProjectReport(project_path=str(
        git_dir / "TeamProject"), project_name="TeamProject", project_repo=Repo(str(git_dir / "TeamProject")))

    is_group = team_report.statistics.get(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    total_authors = team_report.statistics.get(
        ProjectStatCollection.TOTAL_AUTHORS.value)
    authors_per_file = team_report.statistics.get(
        ProjectStatCollection.AUTHORS_PER_FILE.value)

    assert is_group is not None and is_group.value is True  # Group project
    assert total_authors is not None and total_authors.value == 2
    assert authors_per_file is not None and isinstance(
        authors_per_file.value, dict)
    assert "feature1.py" in authors_per_file.value
    assert "feature2.py" in authors_per_file.value
    assert authors_per_file.value["feature1.py"] == 1
    assert authors_per_file.value["feature2.py"] == 1
