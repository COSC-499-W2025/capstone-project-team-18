from pathlib import Path
import shutil
import tempfile
from git import Repo
import datetime

import pytest

from classes.analyzer import CodeFileAnalyzer, get_appropriate_analyzer
from classes.statistic import FileStatCollection


def test_is_git_repo_true_and_false(tmp_path: Path):
    # Repo case
    repo_dir = tmp_path / "RepoProject"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    # create a python file and commit so analyzer can read it
    file_path = repo_dir / "file.py"
    file_path.write_text("print('hello')\n")
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Alice")
        cfg.set_value("user", "email", "alice@example.com")
    repo.index.add([str(file_path.relative_to(repo_dir))])
    repo.index.commit("Initial commit")

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file_path.relative_to(repo_dir)), repo)

    assert analyzer.is_git_tracked is True

    # Non-repo case
    nonrepo_dir = tmp_path / "NoGit"
    nonrepo_dir.mkdir()
    nr_file = nonrepo_dir / "nr.py"
    nr_file.write_text("print('no git')\n")
    analyzer_nr = get_appropriate_analyzer(
        str(nonrepo_dir), str(nr_file.relative_to(nonrepo_dir)))
    assert analyzer_nr.is_git_tracked is False


def test_get_file_commit_percentage_two_authors(tmp_path: Path):
    temp_dir = tempfile.mkdtemp(dir=str(tmp_path))
    try:
        project_dir = Path(temp_dir) / "ContribProject"
        project_dir.mkdir()
        repo = Repo.init(project_dir)

        file_path = project_dir / "shared.py"

        # Initial content by Alice (3 lines)
        file_path.write_text("line1\nline2\nline3\n")
        with repo.config_writer() as cfg:
            cfg.set_value("user", "name", "Alice")
            cfg.set_value("user", "email", "alice@example.com")
        repo.index.add([str(file_path.relative_to(project_dir))])
        repo.index.commit("Alice initial commit")

        # Bob changes five lines ( overwrites all but the first
        with repo.config_writer() as cfg:
            cfg.set_value("user", "name", "Bob")
            cfg.set_value("user", "email", "bob@example.com")
        # Modify lines
        file_path.write_text(
            "line1\nbob_line2\nbob_line3\nbob_line4\nbob_line5")
        repo.index.add([str(file_path.relative_to(project_dir))])
        repo.index.commit("Bob creates 5 lines")

        # Analyzer for the file
        analyzer = get_appropriate_analyzer(
            str(project_dir), str(file_path.relative_to(project_dir)), repo)

        assert isinstance(analyzer, CodeFileAnalyzer)
        assert analyzer.is_git_tracked is True

        # Alice percentage should be ~33.33
        analyzer.email = "alice@example.com"
        report = analyzer.analyze()
        alice_pct = report.get_value(
            FileStatCollection.PERCENTAGE_LINES_COMMITTED.value)
        assert alice_pct is not None
        assert pytest.approx(alice_pct, 0.01) == 20.00

        # Bob percentage should be ~66.67
        analyzer.email = "bob@example.com"
        report = analyzer.analyze()
        bob_pct = report.get_value(
            FileStatCollection.PERCENTAGE_LINES_COMMITTED.value)
        assert bob_pct is not None
        assert pytest.approx(bob_pct, 0.01) == 80.00

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_file_not_comitted_in_git_repo(tmp_path: Path):
    """
    Test that if there is a file in a git repo that has not been committed yet,
    the _get_file_commit_percentage method returns None and does not create
    a statistic
    """

    repo_dir = tmp_path / "RepoWithUncommittedFile"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    # commit a different file first
    committed_file = repo_dir / "committed.py"
    committed_file.write_text("print('committed file')\n")
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Bob")
        cfg.set_value("user", "email", "bob@example.com")

        repo.index.add([str(committed_file.relative_to(repo_dir))])
        repo.index.commit("Initial commit")

    # create a python file but do not commit it
    file_path = repo_dir / "uncommitted.py"
    file_path.write_text("print('uncommitted file')\n")
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Charlie")
        cfg.set_value("user", "email", "charlie@example.com")

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file_path.relative_to(repo_dir)), repo)

    assert analyzer.is_git_tracked is False

    fr = analyzer.analyze()

    assert fr.get_value(
        FileStatCollection.PERCENTAGE_LINES_COMMITTED.value) is None


def test_git_file_has_local_changes(tmp_path: Path):
    """
    Test that if there is a file in a git repo that has local changes,
    the is_git_tracked attribute is still True
    """

    repo_dir = tmp_path / "RepoWithLocalChanges"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    # commit a file first
    file_path = repo_dir / "file_with_changes.py"
    file_path.write_text("print('original content')\n")
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Dana")
        cfg.set_value("user", "email", "dana@example.com")

        repo.index.add([str(file_path.relative_to(repo_dir))])
        repo.index.commit("Initial commit")

    # another person adds a line
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Evan")
        cfg.set_value("user", "email", "evan@example.com")
        file_path.write_text(
            "print('original content')\nprint('added by Evan')\n")
        repo.index.add([str(file_path.relative_to(repo_dir))])
        repo.index.commit("Evan adds a line")

    # make local changes to the file
    file_path.write_text("print('modified content')\n")

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file_path.relative_to(repo_dir)), repo, email="dana@example.com")

    assert analyzer.is_git_tracked is True
    fr = analyzer.analyze()
    assert fr.get_value(
        FileStatCollection.PERCENTAGE_LINES_COMMITTED.value) == 50.0


def test_earliest_commit_and_last_commit(tmp_path: Path):
    """
    This test creates commits in a git repo with different
    authored and commit dates to ensure that the eariliest
    date and last commit date are correctly identified.
    """

    repo_dir = tmp_path / "RepoWithDates"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    file_path = repo_dir / "dated_file.py"
    file_path.write_text("print('first commit')\n")
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Frank")
        cfg.set_value("user", "email", "frank@example.com")
    repo.index.add([str(file_path.relative_to(repo_dir))])
    repo.index.commit("First commit",
                      author_date="2023-01-01 10:00:00")

    # Second commit with later authored date
    file_path.write_text("print('second commit')\n")
    repo.index.add([str(file_path.relative_to(repo_dir))])
    repo.index.commit("Second commit",
                      author_date="2023-01-02 10:00:00")

    # Third commit with latests authored date
    file_path.write_text("print('third commit')\n")
    repo.index.add([str(file_path.relative_to(repo_dir))])
    repo.index.commit("Third commit",
                      author_date="2023-01-03 10:00:00")

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file_path.relative_to(repo_dir)), repo)

    fr = analyzer.analyze()
    earliest_date = fr.get_value(FileStatCollection.DATE_CREATED.value)
    last_date = fr.get_value(FileStatCollection.DATE_MODIFIED.value)

    assert isinstance(earliest_date, datetime.datetime)
    assert isinstance(last_date, datetime.datetime)

    assert earliest_date == datetime.datetime(2023, 1, 1, 10, 0, 0)
    assert last_date == datetime.datetime(2023, 1, 3, 10, 0, 0)
