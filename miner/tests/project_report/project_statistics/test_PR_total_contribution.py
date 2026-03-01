from pathlib import Path
import tempfile
from git import Repo
import shutil
import pytest

from src.utils.pathing_utils import unzip_file
from src.core.analyzer import extract_file_reports, analyzer_util
from src.core.project_discovery.project_discovery import discover_projects, ProjectLayout
from src.core.statistic import ProjectStatCollection
from src.core.report import ProjectReport
from src.core.report.project.project_statistics import ProjectTotalContributionPercentage
from src.database.api.models import UserConfigModel


@pytest.fixture(autouse=True)
def mock_analyzer_db_engine(monkeypatch, blank_db):
    monkeypatch.setattr(analyzer_util, "get_engine", lambda: blank_db)


@pytest.fixture
def discovered_project(resource_dir, tmp_path):
    project_filename = "sample_git_project_one_author.zip"
    zipped_file = Path(resource_dir) / project_filename

    unzip_file(str(zipped_file), str(tmp_path))
    return discover_projects(tmp_path)[0]


@pytest.mark.parametrize(
    "email,expected_percentage",
    [
        ("sikora.samj@gmail.com", 100),
        ("bob@gmail.com", 0),
        (None, None),
    ],
)
def test_verify_accurate_contribution_percentage(
    discovered_project, email, expected_percentage, mock_readme_analysis
):
    """
    Verify total contribution percentage for different user emails.
    """
    file_reports = extract_file_reports(
        discovered_project,
        UserConfigModel(user_email=email)
    )

    project_report = ProjectReport(
        project_name=discovered_project.name,
        project_path=str(discovered_project.root_path),
        project_repo=discovered_project.repo,
        file_reports=file_reports,
        user_email=email,
        calculator_classes=[ProjectTotalContributionPercentage],
    )

    assert (
        project_report.get_value(
            ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value
        )
        == expected_percentage
    )


def test_total_contribution_percentage_negative_zero_contribution(tmp_path: Path, mock_readme_analysis):
    """Test that 0% is returned when user has no contribution to any file"""

    temp_dir = tempfile.mkdtemp(dir=str(tmp_path))
    project_dir = Path(temp_dir) / "NoContributionProject"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    # fileA.py: John only
    with repo.config_writer() as config:
        config.set_value("user", "name", "John")
        config.set_value("user", "email", "john@example.com")
    (project_dir / "fileA.py").write_text("# Created by John\nprint('John')\n")
    repo.index.add(["fileA.py"])
    repo.index.commit("John creates fileA")

    # fileB.py: Bob only
    with repo.config_writer() as config:
        config.set_value("user", "name", "Bob")
        config.set_value("user", "email", "bob@example.com")
    (project_dir / "fileB.py").write_text("# Created by Bob\nprint('Bob')\n")
    repo.index.add(["fileB.py"])
    repo.index.commit("Bob creates fileB")

    project_files = ProjectLayout(
        name="NoContributionProject",
        root_path=project_dir,
        file_paths=[Path("fileA.py"), Path("fileB.py")],
        repo=repo
    )

    user_config = UserConfigModel()
    user_config.user_email = "charlie@example.com"

    fr = extract_file_reports(project_files, user_config)

    pr = ProjectReport(file_reports=fr,
                       project_path=str(project_dir),
                       project_repo=Repo(str(project_dir)),
                       project_name="NoContributionProject",
                       user_email="charlie@example.com",
                       calculator_classes=[ProjectTotalContributionPercentage])

    # Charlie contributed 0% since not in any file reports
    contrib_flags = [f.is_info_file is False for f in fr]
    assert contrib_flags.count(True) == 0
    assert contrib_flags.count(False) == 2

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_total_contribution_percentage_single_file_full_contribution(tmp_path: Path, mock_readme_analysis):
    """Test 100% contribution when user is sole contributor"""

    temp_dir = tempfile.mkdtemp(dir=str(tmp_path))
    project_dir = Path(temp_dir) / "SingleAuthorProject"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    with repo.config_writer() as config:
        config.set_value("user", "name", "Alice")
        config.set_value("user", "email", "alice@example.com")
    (project_dir / "main.py").write_text("# Alice's work\nprint('hello')\n")
    repo.index.add(["main.py"])
    repo.index.commit("Alice creates main")

    project_files = ProjectLayout(
        name="SingleAuthorProject",
        root_path=project_dir,
        file_paths=[Path("main.py")],
        repo=repo
    )

    user_config = UserConfigModel()
    user_config.user_email = "alice@example.com"

    fr = extract_file_reports(project_files, user_config)

    pr = ProjectReport(file_reports=fr,
                       project_path=str(project_dir),
                       project_repo=Repo(str(project_dir)),
                       project_name="SingleAuthorProject",
                       user_email="alice@example.com",
                       calculator_classes=[ProjectTotalContributionPercentage])

    assert pr.get_value(
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value) == 100.0

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_total_contribution_percentage_three_way_split(tmp_path: Path, mock_readme_analysis):
    """Test contribution percentage with three equal contributors"""

    temp_dir = tempfile.mkdtemp(dir=str(tmp_path))
    project_dir = Path(temp_dir) / "ThreeWayProject"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    # Each author creates one file with equal lines
    for author, email, filename in [
        ("Alice", "alice@example.com", "fileA.py"),
        ("Bob", "bob@example.com", "fileB.py"),
        ("Charlie", "charlie@example.com", "fileC.py")
    ]:
        with repo.config_writer() as config:
            config.set_value("user", "name", author)
            config.set_value("user", "email", email)
        (project_dir / filename).write_text(f"# {author}\nline1\nline2\n")
        repo.index.add([filename])
        repo.index.commit(f"{author} creates {filename}")

    project_files = ProjectLayout(
        name="ThreeWayProject",
        root_path=project_dir,
        file_paths=[Path("fileA.py"), Path("fileB.py"), Path("fileC.py")],
        repo=repo
    )

    user_config = UserConfigModel()
    user_config.user_email = "alice@example.com"

    fr = extract_file_reports(project_files, user_config)

    pr = ProjectReport(file_reports=fr,
                       project_path=str(project_dir),
                       project_repo=Repo(str(project_dir)),
                       project_name="ThreeWayProject",
                       user_email="alice@example.com",
                       calculator_classes=[ProjectTotalContributionPercentage])

    # Alice should have ~33.33%
    assert pytest.approx(pr.get_value(
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value), 0.1) == 33.33

    shutil.rmtree(temp_dir, ignore_errors=True)
