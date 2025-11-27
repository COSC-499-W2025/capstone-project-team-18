from pathlib import Path

from git import Repo


def commit_file_to_repo(repo: Repo, contributor: list[str], file: Path, repo_path: Path, commit_msg: str, author_date: str) -> None:
    '''
    Commits a file to a repository

    Args:
        repo (Repo)
        contributor (list[str]): A list with two elements: the name of the contributor and their email
        file (Path): The file that is being committed
        repo_path (Path): Path to the repository
        commit_msg (str)
        author_date (str): Optional, str of a date in the format "YYYY-MM-DD HH:MM:SS" or empty string

    '''
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", contributor[0])
        cfg.set_value("user", "email", contributor[1])
    repo.index.add([str(file.relative_to(repo_path))])  # stage the file

    # commit the file
    if author_date is not None:
        repo.index.commit(commit_msg, author_date=author_date)
    else:
        repo.index.commit(commit_msg, author_date=author_date)
