from pathlib import Path
import datetime

from git import Repo
import pytest

from src.classes.analyzer import CodeFileAnalyzer, get_appropriate_analyzer
from src.classes.statistic import FileStatCollection
from tests.utils.helper_functions import get_temp_file, get_temp_local_dir
from tests.analyze.git_helper_functions import commit_file_to_repo


@pytest.fixture(scope="function")
def temp_git_repo(tmp_path: Path):
    '''
    Create a reusable git repository
    with an 'app.py' file that is committed by
    Alice. The file contains:
    ```
    print('line one')
    print('line two')
    # A comment from Alice
    '''
    # create the repository
    repo_directory = tmp_path / "temp-repository"
    repo_directory.mkdir()
    repo = Repo.init(repo_directory)

    content = '''print('line one')
    \nprint('line two')
    \n# A comment from Alice'''

    # make and commit the file to the repo
    file = get_temp_file(filename="app.py",
                         content=content,
                         path=repo_directory)

    commit_file_to_repo(repo=repo, contributor=["Alice", "alice@test.com"], file=file,
                        repo_path=repo_directory, commit_msg="Initial commit", author_date="2024-01-01 00:00:00",)

    return repo, repo_directory, file


def test_is_git_repo_true_and_false(temp_git_repo, tmp_path: Path):
    '''
    Test that the `is_git_tracked()` function returns `True` for a
    repository with a file committed, and `False` for a non-repository
    directory (the file is not committed)
    '''
    repo, repo_dir, file = temp_git_repo

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file.relative_to(repo_dir)), repo)

    assert analyzer.is_git_tracked is True

    # Directory that isn't a repository
    nonrepo_dir = tmp_path / "NoGit"
    nonrepo_dir.mkdir()

    local_dir = get_temp_local_dir(dir_name='local-dir', path=tmp_path)
    local_file = get_temp_file(
        filename='no-repo.py', content='print("not a git repo")', path=tmp_path / 'local-dir')

    analyzer = get_appropriate_analyzer(
        str(local_dir), str(local_file.relative_to(local_dir)))
    assert analyzer.is_git_tracked is False


def test_get_file_commit_percentage_two_authors(temp_git_repo, tmp_path: Path):
    '''
    Test the contribution calculation is correct using a file that has two contributors.
    First, Alice creates app.py with 3 lines. Then, Bob overwrites Alice's third line
    and adds three of his own. In the end:
    - 2/5 lines are from Alice
    - 3/5 lines are from Bob
    '''
    # Have Alice initally write to app.py
    repo, repo_dir, file = temp_git_repo

    # Commit Bob's changes (overwrites Alice's last line and add 3 new lines)
    file.write_text(
        "print('line one')\nprint('line two')\n#comment-bob-1\n#comment-bob-2\nprint('line5')")

    commit_file_to_repo(repo=repo, contributor=['Bob', 'bob@test.com'], file=file,
                        repo_path=repo_dir, commit_msg='Bob commits app.py and writes over Alice', author_date="",)

    # Analyze the file
    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file.relative_to(repo_dir)), repo)
    assert isinstance(analyzer, CodeFileAnalyzer)
    assert analyzer.is_git_tracked is True

    # Get Alice's contribution stat
    analyzer.email = "alice@test.com"
    alice_pct = analyzer._get_file_commit_percentage()
    assert alice_pct is not None

    # Alice's contribution should be 40% ± 1%
    assert pytest.approx(alice_pct, 0.01) == 40.00

    # Get Bob's contribution stat
    analyzer.email = "bob@test.com"
    bob_pct = analyzer._get_file_commit_percentage()
    assert bob_pct is not None

    # Bob's contribution should be 75% ± 1%
    assert pytest.approx(bob_pct, 0.01) == 60.00


def test_file_not_committed_in_git_repo(temp_git_repo, tmp_path: Path):
    """
    Test that if there is a file in a git repo that has not been committed yet,
    the `_get_file_commit_percentage()` function returns `None` and does not create
    a statistic.
    """
    repo, repo_dir, file = temp_git_repo

    # Create a new file
    file = get_temp_file(filename="uncomitted.py",
                         content="print('this file has not been comitted')", path=repo_dir)

    # Configure user credentials, but don't commit the file
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Spencer")
        cfg.set_value("user", "email", "spencer@test.com")

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file.relative_to(repo_dir)), repo)

    assert analyzer.is_git_tracked is False

    fr = analyzer.analyze()

    assert fr.get_value(
        FileStatCollection.PERCENTAGE_LINES_COMMITTED.value) is None


def test_git_file_has_local_changes(temp_git_repo, tmp_path: Path):
    """
    Test that if there is a file in a git repo that has local changes,
    the `is_git_tracked` attribute is still `True`. We have Bob
    """
    repo, repo_dir, file = temp_git_repo

    # Commit Bob's changes (overwrites Alice's last line and adds a new line)
    file.write_text(
        "print('line one')\nprint('line two')\nprint('added by Bob)")

    commit_file_to_repo(repo=repo, contributor=['Bob', 'bob@test.com'], file=file,
                        repo_path=repo_dir, commit_msg='Bob commits app.py and writes over Alice', author_date="",)

    # Bob makes a local change, but doesn't commit it
    file.write_text("print('new file content')")

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file.relative_to(repo_dir)), repo, email="bob@test.com")

    assert analyzer.is_git_tracked is True


def test_earliest_commit_and_last_commit(temp_git_repo, tmp_path: Path):
    """
    This test creates commits in a git repo with different
    authored and commit dates to ensure that the eariliest
    date and last commit date are correctly identified.
    """
    repo, repo_dir, file = temp_git_repo

    # Commit Bob's changes (overwrites Alice's last line and adds a new line)
    # on April 12, 2025 at 9:00 A.M.
    file.write_text(
        "print('line one')\nprint('line two')\nprint('added by Bob)")

    commit_file_to_repo(repo=repo, contributor=['Bob', 'bob@test.com'], file=file, repo_path=repo_dir,
                        commit_msg='Bob commits app.py and writes over Alice', author_date="2025-04-12 09:00:00",)

    # Make another commit on April 12, 2025 at 1:00 P.M.
    file.write_text(
        "print('line one')\nprint('line two')\nprint('added by Bob)\nprint('a new line!)")

    commit_file_to_repo(repo=repo, contributor=['Bob', 'bob@test.com'], file=file, repo_path=repo_dir,
                        commit_msg='Bob commits app.py and writes over Alice', author_date="2025-04-12 13:00:00",)

    # Make another commit on May 9, 2025 at 5:35 P.M.
    file.write_text(
        "print('line one')\nprint('line two')\nprint('added by Bob)\n")

    commit_file_to_repo(repo=repo, contributor=['Bob', 'bob@test.com'], file=file, repo_path=repo_dir,
                        commit_msg='Bob commits app.py and writes over Alice', author_date="2025-05-09 17:35:00",)

    analyzer = get_appropriate_analyzer(
        str(repo_dir), str(file.relative_to(repo_dir)), repo)

    fr = analyzer.analyze()
    earliest_date = fr.get_value(FileStatCollection.DATE_CREATED.value)
    last_date = fr.get_value(FileStatCollection.DATE_MODIFIED.value)

    assert isinstance(earliest_date, datetime.datetime)
    assert isinstance(last_date, datetime.datetime)

    assert earliest_date == datetime.datetime(2024, 1, 1, 0, 0, 0)
    assert last_date == datetime.datetime(2025, 5, 9, 17, 35, 0)
