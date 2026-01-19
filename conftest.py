"""
This file will run everytime pytest
starts running tests. It is used to
make global changes to the testing environment.
"""

from pathlib import Path
import pytest
from git import Repo
import os
from src.utils.project_discovery.project_discovery import ProjectFiles
from src.classes.statistic import Statistic, StatisticIndex
from src.classes.report import UserReport, ProjectReport
import tempfile
import shutil
from sqlalchemy import create_engine
from src.database.base import Base


@pytest.fixture
def create_temp_file():
    """
    Returns a callable to create a new file with
    the provided name, in the provided path,
    with the provided content in the provided encoding.
    """

    def _create(filename: str, content: str, path: Path, encoding: str = "utf-8") -> list[str]:

        path_full = path / filename

        # Make directory if not exits
        path_full.parent.mkdir(parents=True, exist_ok=True)

        path_full.write_text(content, encoding=encoding)

        return [str(path), filename]

    return _create


@pytest.fixture
def make_project_file(create_temp_file):
    """
    Returns a callable that makes the given ProjectFile.
    Every file in the project has one line in it.

    Only works for project_files without Repos.
    """

    def _create(project_file: ProjectFiles):
        project_dir = Path(project_file.root_path)

        if not project_file.name == project_dir.name:
            raise ValueError(
                "Miss configured project_file. root_path dir does not match ProjectFile name")

        project_dir.mkdir(parents=True, exist_ok=True)

        for file in project_file.file_paths:

            create_temp_file(file, "Junk Content", project_dir)

    return _create


@pytest.fixture
def resource_dir():
    """
    This fixture points the the resources folder where we have
    some static files that help with testing
    """
    return Path(__file__).parent / "tests/resources"


@pytest.fixture
def blank_db():
    """
    This fixtures returns a in memory database which will be discarded
    when the test is done.
    """

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    yield engine


def commit_as(repo: Repo, author_name: str, author_email: str,
              file_path: Path, content: str, message: str,
              project_dir: Path, append: bool = False):
    """
    Write content to a file (overwrite or append), stage it, and commit it
    under a specific author.
    """

    with repo.config_writer() as config:
        config.set_value("user", "name", author_name)
        config.set_value("user", "email", author_email)

    # Append or overwrite
    if append and file_path.exists():
        with file_path.open("a", encoding="utf-8") as f:
            f.write(content)
    else:
        file_path.write_text(content, encoding="utf-8")

    relative_path = str(file_path.relative_to(project_dir))
    repo.index.add([relative_path])
    repo.index.commit(message)


@pytest.fixture(scope="session", autouse=True)
def cleanup_tmp_files():
    """
    Clean up leftover pytest tmp files in the system temp directory after the
    test session finishes. Removes files and directories that begin with
    'python-test-discovery-' or 'artifact_miner' or 'python-test-results-'.
    """

    # Run tests first
    yield

    tmp_dir = Path(tempfile.gettempdir())
    patterns = ("python-test-discovery-",
                "artifact_miner_", "python-test-results-")

    for entry in list(tmp_dir.iterdir()):
        try:
            if any(entry.name.startswith(p) for p in patterns):
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    try:
                        entry.unlink()
                    except Exception:
                        try:
                            os.remove(entry)
                        except Exception:
                            pass
        except Exception:
            # Ignore cleanup errors so they do not fail the test session
            pass


@pytest.fixture
def user_report_from_stats():
    """
    Return a callable that builds a UserReport from a list of Statistics.
    """
    def _create(statistics: list[Statistic], report_name: str = "UserReportTest") -> UserReport:
        return UserReport([], report_name, statistics=StatisticIndex(statistics))

    return _create


@pytest.fixture
def project_report_from_stats():
    """
    Return a callable that builds a Project from a list of Statistics.
    """
    def _create(statistics: list[Statistic], project_name: str = "TESTING ONLY SHOULD SEE THIS IN PYTEST") -> ProjectReport:
        return ProjectReport([], project_name=project_name, statistics=StatisticIndex(statistics))

    return _create


@pytest.fixture
def temp_text_file(tmp_path: Path, create_temp_file) -> list[str]:
    """
    Creates a temporary text file.

    Returns:
        list[str] : [tmp_path, "sample.txt"]
    """

    return create_temp_file("sample.txt", "Myles Jack wasn't down\n", tmp_path)


@pytest.fixture
def project_shared_file(tmp_path: Path) -> ProjectFiles:
    """
    Creates a project called "SharedFile" that has one file
    "shared.py" that was modified by three authors.
    """

    project_dir = tmp_path / "SharedFile"
    project_dir.mkdir()
    repo = Repo.init(project_dir)
    filename = "shared.py"
    file_path = project_dir / filename

    # Alice creates file
    commit_as(
        repo,
        author_name="Alice",
        author_email="alice@example.com",
        file_path=file_path,
        content="# Initial version",
        message="Alice's initial commit",
        project_dir=project_dir
    )

    # Bob modifies it
    commit_as(
        repo,
        author_name="Bob",
        author_email="bob@example.com",
        file_path=file_path,
        content="# Modified by Bob",
        message="Bob's modification",
        project_dir=project_dir
    )

    # Charlie modifies it
    commit_as(
        repo,
        author_name="Charlie",
        author_email="charlie@example.com",
        file_path=file_path,
        content="# Modified by Charlie",
        message="Charlie's modification",
        project_dir=project_dir
    )

    return ProjectFiles(
        name="SharedFile",
        root_path=str(project_dir),
        file_paths=[filename],
        repo=repo
    )


@pytest.fixture
def project_realistic(tmp_path: Path, create_temp_file) -> ProjectFiles:
    """
    Creates a realistic multi-folder git project with many files and
    multiple authors contributing across commits.

    Structure:
        /app
            __init__.py
            main.py
            utils/helpers.py
        /tests
            test_main.py
        /db
            schema.sql
        /scripts
            bootstrap.sh
        /docs
            README.md

    Returns:
        ProjectFiles: The project description for the created repo.
    """

    project_dir = tmp_path / "RealisticProject"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    # Create directories
    app_dir = project_dir / "app"
    utils_dir = app_dir / "utils"
    tests_dir = project_dir / "tests"
    db_dir = project_dir / "db"
    scripts_dir = project_dir / "scripts"
    docs_dir = project_dir / "docs"

    for d in [app_dir, utils_dir, tests_dir, db_dir, scripts_dir, docs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Create untracked database file
    create_temp_file("db.db", "here is db stored", db_dir)

    # Initial commit by Alice
    commit_as(
        repo, "Alice", "alice@example.com",
        app_dir / "main.py",
        "def main():\n    return 'Hello'",
        "Initial app structure",
        project_dir
    )

    # Bob adds helpers + tests
    commit_as(
        repo, "Bob", "bob@example.com",
        utils_dir / "helpers.py",
        "\ndef helper():\n    return 42",
        "Add helpers",
        project_dir,
        True
    )

    commit_as(
        repo, "Bob", "bob@example.com",
        tests_dir / "test_main.py",
        "def test_main():\n    assert True",
        "Add tests",
        project_dir
    )

    # Charlie adds schema
    commit_as(
        repo, "Charlie", "charlie@example.com",
        db_dir / "schema.sql",
        "CREATE TABLE users\n(id INTEGER PRIMARY KEY,\n name TEXT\n);",
        "Add initial DB schema",
        project_dir
    )

    # Bob edits schema
    commit_as(
        repo, "Bob", "bob@example.com",
        db_dir / "schema.sql",
        "CREATE TABLE users\n(id INTEGER PRIMARY KEY,\n name NORMAL_TEXT\n);",
        "Edited DB schema",
        project_dir
    )

    # Dana writes docs
    commit_as(
        repo, "Dana", "dana@example.com",
        docs_dir / "README.md",
        "# RealisticProject\n\nA sample project for testing.\n",
        "Add documentation",
        project_dir
    )

    # Bob adds docs
    commit_as(
        repo, "Bob", "bob@example.com",
        docs_dir / "README.md",
        "## And I am adding more!\n - Here is my new line",
        "Add more documentation",
        project_dir,
        True
    )

    # Eve writes scripts
    commit_as(
        repo, "Eve", "eve@example.com",
        scripts_dir / "bootstrap.sh",
        "#!/bin/bash\necho 'Bootstrapping...'",
        "Bootstrap script",
        project_dir
    )

    return ProjectFiles(
        name="RealisticProject",
        root_path=str(project_dir),
        file_paths=[
            "app/main.py",
            "app/utils/helpers.py",
            "tests/test_main.py",
            "db/schema.sql",
            "db/db.db",
            "scripts/bootstrap.sh",
            "docs/README.md",
        ],
        repo=repo
    )


@pytest.fixture
def project_no_git_dir(tmp_path: Path) -> ProjectFiles:
    """
    Creates a not git project with two python files.

    Returns:
        tuple(str, list[str]) : Path to project folder, realtive
            path to files in project.
    """
    project_dir = tmp_path / "NoGitProject"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('No git')")
    (project_dir / "utils.py").write_text("# Utils")

    return ProjectFiles(
        name="NoGitProject",
        root_path=str(project_dir),
        file_paths=["main.py", "utils.py"],
        repo=None
    )
