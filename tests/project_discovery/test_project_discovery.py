from pathlib import Path
import zipfile
import pytest
from git import Repo

import shutil
import tempfile
from src.core.project_discovery.project_discovery import ProjectLayout
from src.core.analyzer import extract_file_reports
from src.core.statistic import FileStatCollection
from src.core.project_discovery.project_discovery import discover_projects  # type: ignore  # noqa: E402
from src.core.report import ProjectReport  # type: ignore  # noqa: E402
from src.core.statistic import ProjectStatCollection  # type: ignore  # noqa: E402
from src.core.report.project.project_statistics import ProjectAnalyzeGitAuthorship


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
    assert Path("src/utils/helper.py") in get_files("Assignment2")
    assert Path("src/models/user.py") in get_files("FinalProject")

    # Verify file counts per project
    assert len(get_files("Assignment1")) == 2
    assert len(get_files("Assignment2")) == 4
    assert len(get_files("FinalProject")) == 3

    # Verify git repo is none
    for p in result:
        assert p.repo is None


def test_discover_git_projects(git_dir: Path):
    """Verifies discovery of projects with Git repositories."""
    result = discover_projects(str(git_dir))
    project_names = {p.name for p in result}
    assert {"SoloProject", "TeamProject"} <= project_names
    # Verify file counts
    for p in result:
        if p.name == "SoloProject":
            assert len(p.file_paths) == 1 and Path(
                "solo_work.py") in p.file_paths
            assert p.repo is not None
        elif p.name == "TeamProject":
            assert len(p.file_paths) == 2
            assert Path("feature1.py") in p.file_paths
            assert Path("feature2.py") in p.file_paths
            assert p.repo is not None


def test_identify_project_type(git_dir: Path):
    """Verifies Git-based detection of individual vs group projects."""
    # Single author = individual (False)
    solo_report = ProjectReport(project_path=str(
        git_dir / "SoloProject"), project_name="SoloProject",
        project_repo=Repo(str(git_dir / "SoloProject")), user_email="charlie@example.com",
        calculator_classes=[ProjectAnalyzeGitAuthorship])

    assert solo_report.statistics.get(
        ProjectStatCollection.IS_GROUP_PROJECT.value).value is False

    # Multiple authors = group (True)
    team_report = ProjectReport(project_path=str(
        git_dir / "TeamProject"), project_name="TeamProject",
        project_repo=Repo(str(git_dir / "TeamProject")), user_email="charlie@example.com")
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
    from src.core.project_discovery.project_discovery import discover_projects
    with pytest.raises(FileNotFoundError):
        discover_projects(str(tmp_path / "does_not_exist"))


def test_mac_zip_structure(tmp_path: Path):
    """Verifies handling of Mac-created zip files with parent folders and metadata."""
    mac_zip_path = Path(__file__).parent.parent / \
        "resources" / "mac_projects.zip"
    extract_dir = tmp_path / "mac_extracted"
    extract_dir.mkdir()
    import zipfile
    with zipfile.ZipFile(mac_zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    result = discover_projects(str(extract_dir))
    project_names = {str(p.name) for p in result}
    # Should skip parent "Projects" folder and __MACOSX metadata
    assert "Projects" not in project_names
    assert "__MACOSX" not in project_names
    # Should find ProjectA and ProjectB as top-level projects
    assert "ProjectA" in project_names
    assert "ProjectB" in project_names

    def get_files(name):
        for p in result:
            if p.name == name:
                return [str(f) for f in p.file_paths]
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
        git_dir / "SoloProject"),
        project_name="SoloProject",
        project_repo=Repo(str(git_dir / "SoloProject")),
        user_email="charlie@example.com",
        calculator_classes=[ProjectAnalyzeGitAuthorship]
    )

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
        git_dir / "TeamProject"),
        project_name="TeamProject",
        project_repo=Repo(str(git_dir / "TeamProject")),
        user_email="charlie@example.com",
        calculator_classes=[ProjectAnalyzeGitAuthorship]
    )

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


def test_info_files_exist(tmp_path: Path):
    """Given partial contribution, a project report will exist but
    include only full reports on some files. In this case, 2/4 are contrubted to
    and the other 2 are info files
    """

    temp_dir = tempfile.mkdtemp(dir=str(tmp_path))
    project_dir = Path(temp_dir) / "PartialProject"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    # Two files created by Alice (not the user)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Alice")
        config.set_value("user", "email", "alice@example.com")
    (project_dir / "a1.py").write_text("# by Alice\n")
    repo.index.add(["a1.py"])
    repo.index.commit("Alice commit a1")
    (project_dir / "a2.py").write_text("# by Alice\n")
    repo.index.add(["a2.py"])
    repo.index.commit("Alice commit a2")

    # Two files created by Charlie (the user)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Charlie")
        config.set_value("user", "email", "charlie@example.com")
    (project_dir / "c1.py").write_text("# by Charlie\n")
    repo.index.add(["c1.py"])
    repo.index.commit("Charlie commit c1")
    (project_dir / "c2.py").write_text("# by Charlie\n")
    repo.index.add(["c2.py"])
    repo.index.commit("Charlie commit c2")

    project_files = ProjectLayout(
        name="PartialProject",
        root_path=project_dir,
        file_paths=[Path("a1.py"), Path("a2.py"),
                    Path("c1.py"), Path("c2.py")],
        repo=repo
    )

    fr = extract_file_reports(project_files, "charlie@example.com")

    # Four file reports included
    assert len(fr) == 4

    # Exactly two files should be marked as contributed to by Charlie
    contrib_flags = [f.get_value(
        FileStatCollection.CONTRIBUTED_TO.value) for f in fr]
    assert contrib_flags.count(True) == 2
    assert contrib_flags.count(False) == 2

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_partial_project_contribution(tmp_path: Path):
    """Test that given a portion of project with contribution, that the correct contribution flags are set
    Additionlly, the correct project errors should be thrown"""
    from src.services.mining_service import ProjectError
    from src.utils.errors import ErrorCode

    temp_dir = tempfile.mkdtemp(dir=str(tmp_path))

    # Project A: user contributes (Charlie)
    proj_a = Path(temp_dir) / "ProjectA"
    proj_a.mkdir()
    repo_a = Repo.init(proj_a)
    with repo_a.config_writer() as cfg:
        cfg.set_value("user", "name", "Charlie")
        cfg.set_value("user", "email", "charlie@example.com")
    (proj_a / "main.py").write_text("# by Charlie\n")
    repo_a.index.add(["main.py"])
    repo_a.index.commit("Charlie commit")

    # Project B: user contributes to one file among others
    proj_b = Path(temp_dir) / "ProjectB"
    proj_b.mkdir()
    repo_b = Repo.init(proj_b)
    with repo_b.config_writer() as cfg:
        cfg.set_value("user", "name", "Alice")
        cfg.set_value("user", "email", "alice@example.com")
    (proj_b / "lib.py").write_text("# by Alice\n")
    repo_b.index.add(["lib.py"])
    repo_b.index.commit("Alice commit")
    with repo_b.config_writer() as cfg:
        cfg.set_value("user", "name", "Charlie")
        cfg.set_value("user", "email", "charlie@example.com")
    (proj_b / "util.py").write_text("# by Charlie\n")
    repo_b.index.add(["util.py"])
    repo_b.index.commit("Charlie commit")

    # Project C: no user contributions (only Alice)
    proj_c = Path(temp_dir) / "ProjectC"
    proj_c.mkdir()
    repo_c = Repo.init(proj_c)
    with repo_c.config_writer() as cfg:
        cfg.set_value("user", "name", "Alice")
        cfg.set_value("user", "email", "alice@example.com")
    (proj_c / "only.py").write_text("# by Alice only\n")
    repo_c.index.add(["only.py"])
    repo_c.index.commit("Alice commit only")

    # below is mock of start_miner behaviour
    layouts = [
        ProjectLayout(name="ProjectA", root_path=proj_a,
                      file_paths=[Path("main.py")], repo=repo_a),
        ProjectLayout(name="ProjectB", root_path=proj_b, file_paths=[
                      Path("lib.py"), Path("util.py")], repo=repo_b),
        ProjectLayout(name="ProjectC", root_path=proj_c,
                      file_paths=[Path("only.py")], repo=repo_c),
    ]

    reports = []
    errors = []

    for layout in layouts:
        fr = extract_file_reports(layout, "charlie@example.com")
        pr = ProjectReport(file_reports=fr,
                           project_path=str(layout.root_path),
                           project_name=layout.name,
                           project_repo=layout.repo,
                           user_email="charlie@example.com")
        reports.append(pr)
        if pr.contributed_to is False:
            errors.append(ProjectError(project_name=layout.name,
                                       error_code=ErrorCode.NO_RELEVANT_FILES.value,
                                       error_message=f"No user contribution in {layout.name}"))

    # Two projects should show contributed_to == True, one should be False
    contributed_flags = [r.contributed_to for r in reports]
    assert contributed_flags.count(True) == 2
    assert contributed_flags.count(False) == 1

    # One project error should be produced for the uncontributed project
    assert len(errors) == 1
    assert errors[0].error_code == ErrorCode.NO_RELEVANT_FILES.value

    shutil.rmtree(temp_dir, ignore_errors=True)
