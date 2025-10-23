import sys
from pathlib import Path
import zipfile
import pytest
from git import Repo

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
CLASSES_DIR = SRC_DIR / "classes"

for p in (str(CLASSES_DIR), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.classes.project_discovery import discover_projects, is_group_project  # type: ignore  # noqa: E402


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
def git_zip(tmp_path: Path) -> Path:
    """Creates zip with individual project (1 author) and group project (2 authors)."""
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

    zip_path = tmp_path / "MixedProjects.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for project_dir in [solo_dir, team_dir]:
            for file_path in project_dir.rglob('*'):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(tmp_path))
    return zip_path


def test_discover_multiple_projects(multi_project_zip: Path):
    """Verifies discovery of multiple projects with nested folder structures."""
    result = discover_projects(str(multi_project_zip))
    # Should find all 3 projects
    assert len(result) == 3
    assert "Assignment1" in result and "Assignment2" in result and "FinalProject" in result
    # Verify nested paths are preserved correctly
    assert "src/utils/helper.py" in result["Assignment2"]
    assert "src/models/user.py" in result["FinalProject"]
    # Verify file counts per project
    assert len(result["Assignment1"]) == 2 and len(
        result["Assignment2"]) == 4 and len(result["FinalProject"]) == 3


def test_identify_project_type(git_zip: Path):
    """Verifies Git-based detection of individual vs group projects."""
    # Single author = individual
    assert is_group_project(str(git_zip), "SoloProject") == "individual"
    # Multiple authors = group
    assert is_group_project(str(git_zip), "TeamProject") == "group"


def test_no_git_projects(tmp_path: Path):
    """Verifies handling of projects without Git repositories."""
    zip_path = tmp_path / "NoGitProject.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("BasicProject/main.py", "print('No git')")
        zf.writestr("BasicProject/utils.py", "# Utilities")
    # Project discovery should still work
    result = discover_projects(str(zip_path))
    assert "BasicProject" in result and len(result["BasicProject"]) == 2
    # No Git repo = None
    assert is_group_project(str(zip_path), "BasicProject") is None


def test_invalid_inputs(tmp_path: Path):
    """Verifies proper error handling for invalid zip files and paths."""
    # Nonexistent file should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        discover_projects("/nonexistent/path/file.zip")
    # Corrupted zip file should raise BadZipFile
    bad_zip = tmp_path / "corrupted.zip"
    bad_zip.write_text("This is not a valid zip file")
    with pytest.raises(zipfile.BadZipFile):
        discover_projects(str(bad_zip))
    with pytest.raises(zipfile.BadZipFile):
        is_group_project(str(bad_zip), "AnyProject")
