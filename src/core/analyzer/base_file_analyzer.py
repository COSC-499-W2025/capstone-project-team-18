import datetime
from pathlib import Path
from typing import Optional
from git import GitCommandError, Repo
import hashlib

# database imports are needed for duplicate files checks
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import select, inspect
from src.database.base import get_engine
from src.database.models import FileReportTable


from src.core.report.file_report import FileReport
from src.core.statistic import Statistic, StatisticIndex, FileStatCollection, LANGUAGE_EXTENSIONS
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


class BaseFileAnalyzer:
    """
    Base class for file analysis. Provides a framework for collecting
    file-level statistics.

    To analyze a specific file, extend this class and implement the
    `_process` method. In this method, call the `_process` method of the
    superclass to collect basic statistics, then add any file-specific
    statistics to the `StatisticIndex` (`self.stats`).
    to the `StatisticIndex` (`self.stats`).

    Attributes:
        filepath (str): The path to the file being analyzed.
        stats (StatisticIndex): The index holding collected statistics.
        realtive_path (str): The path to the file relative to the
            top-level project directory.
        repo (Optional[Repo]): The Git repository object if the file
            is part of a Git repository.
        email (Optional[str]): The email of the user analyzing the file.
        github (Optional[str]): The username of the user analyzing the file.

    Statistics:
        - DATE_CREATED
        - DATE_MODIFIED
        - FILE_SIZE_BYTES
    """

    def __init__(self,
                 path_to_top_level_project: str,
                 relative_path: str,
                 repo: Optional[Repo] = None,
                 email: Optional[str] = None,
                 github: Optional[str] = None,
                 language_filter: Optional[list[str]] = None
                 ):

        self.path_to_top_level_project = path_to_top_level_project
        self.relative_path = relative_path
        self.filepath = f"{path_to_top_level_project}/{relative_path}"
        self.repo = repo
        self.email = email
        self.github = github
        self.language_filter = language_filter
        self.stats = StatisticIndex()
        self.blame_info = None
        self.is_git_tracked = self.file_in_git_repo()
        # will either be used as a check or added to fileReport
        self.hashed_content = self.create_hash()

    def file_in_git_repo(self) -> bool:
        """
        Check to see the project is in a git repository and
        if so, that this specific file is tracked by git.
        """

        if self.repo is None:
            return False

        try:
            # Use repo-relative path for blame - GitPython expects a path
            # relative to the repository working tree, not an absolute path
            self.blame_info = self.repo.blame('HEAD', self.relative_path)
            return True
        except (ValueError, GitCommandError, Exception) as e:
            logger.debug(
                f"File not tracked by git or git error: {e}")
            return False

    def should_include(self) -> bool:
        """
        This is a lightweight check to see if the file should be
        included in analysis. By deafult, all files are included.

        A file is excluded if it meets certain criteria:
            - If the user has configured to exclude files of this type
            - If user has given their email, and the file is tracked by git,
                but none of the lines in the file were authored by the user.

        Returns:
            bool: True if the file should be included, False otherwise.
        """

        # If duplicate file exists with matching hash do not include in analysis
        if self.compare_hashes():
            print("hash was checked")
            return False

       # Check language filter
        if self.language_filter:
            if not self._matches_language_filter():
                return False

        if not self.is_git_tracked or not self.email or not self.repo:
            return True

        if self.blame_info is None:
            return True

        # Use the git command "shortlog" to see if a user has contributed to a file.
        git_cmd = self.repo.git
        short_log = git_cmd.shortlog(
            "-s", "-n", "--email", "HEAD", "--", self.relative_path)

        if self.email in short_log:
            return True

        return False

    def create_hash(self) -> str:
        """
        Create a hash of the file's content. Should only occur in the case of a new file, or
        in the case of a matching existing path in order to check against hash value

        Returns:
            str: A hex representation of the resulting MD5 hash
        """
        try:
            with open(self.filepath, "rb") as f:
                hash = hashlib.file_digest(f, "md5")
            return hash.hexdigest()
        except FileNotFoundError:
            logger.exception(f"File not found for {self.filepath}")
            return '0x00'
        except BlockingIOError as e:
            logger.exception(f"Error: {e}")
            return '0x00'

    def compare_hashes(self) -> bool:
        """
        Checks against the database to see if any filepaths are matching,
        upon any matches checks against the hash value to see
        if the content has changed (more accurate than modified date)

        :param self: file analyzer object
        :return: T/F value representing presence of duplicate file
        :rtype: bool
        """

        engine = get_engine()
        with Session(engine) as session:
            inspector = inspect(engine)
            if inspector.has_table('file_report'):
                try:
                    # check if both filepath and hash exist
                    _ = session.execute(
                        select(FileReportTable)
                        .where(FileReportTable.filepath == self.filepath, FileReportTable.file_hash == self.hashed_content)
                        # should result in the only existing column
                    ).scalars().one()
                    logger.exception(
                        f"{self.filepath} already exists and hasn't changes since last analysis")
                    return True  # true if no exception thrown

                # Each project name should be unique, throw error if 0 rows or > 1 rows are returned
                except MultipleResultsFound:
                    logger.error(
                        f'Error: Multiple filepaths found with name "{self.filepath}. Should not be possible under current updates"')
                    return True
                except NoResultFound:
                    return False
            return False  # false if database hasn't been created yet

    def _matches_language_filter(self) -> bool:
        """
        Check if file matches the language filter.

        Returns:
            bool: True if file matches filter or no filter set, False otherwise
        """
        if not self.language_filter:
            return True

        file_ext = Path(self.filepath).suffix.lower()

        # Check each language in the filter
        for lang_name in self.language_filter:
            for coding_lang, extensions in LANGUAGE_EXTENSIONS.items():
                if coding_lang.value.lower() == lang_name.lower():
                    if file_ext in extensions:
                        return True

        return False

    def _process(self) -> None:
        """
        This is the main processing function for the analyzers family
        of classes. It will always be run first before any subclass
        analysis is done.

        Here we collect basic file statistics that are
        common to all file types. That being:
        - Creation date
        - Last modified date
        - Size (in bytes)

        If the file is part of a Git repository, we get the creation
        and last modified dates from the Git commit history. If not,
        we fall back to the filesystem metadata.

        Likewise with any of the analyzers that extend this class,
        you can call this _process method and know that these basic
        statistics will be collected in the self.stats `StatisticIndex`.

        """

        metadata = None
        metadata = Path(self.filepath).stat()

        stats = [
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value,
                      metadata.st_size),
            Statistic(FileStatCollection.FILE_HASH.value, self.hashed_content),
        ]

        if self.is_git_tracked:
            # Get the creation date from the first commit
            # and get the last modified date from the latest commit

            try:
                commits = list(self.repo.iter_commits(  # pyright: ignore[reportOptionalMemberAccess]
                    paths=self.relative_path))
            except Exception as e:
                logger.debug(f"InvalidGitRepositoryError: {e}")
                commits = []

            if commits:
                first_commit = commits[-1]
                latest_commit = commits[0]

                stats.append(Statistic(FileStatCollection.DATE_CREATED.value, datetime.datetime.fromtimestamp(
                    first_commit.authored_date)))
                stats.append(Statistic(FileStatCollection.DATE_MODIFIED.value, datetime.datetime.fromtimestamp(
                    latest_commit.authored_date)))
        else:
            # Fallback to filesystem metadata

            """
            Special note here:

            Linux corrupts the st_birthtime to be the time that
            the file was unzipped.
            Linux's date access actually contains the true birthtime so
            we treat that as DATE_CREATED
            """

            stats.append(Statistic(FileStatCollection.DATE_CREATED.value, datetime.datetime.fromtimestamp(
                metadata.st_atime)))
            stats.append(Statistic(FileStatCollection.DATE_MODIFIED.value, datetime.datetime.fromtimestamp(
                metadata.st_mtime)))

        self.stats.extend(stats)

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a `FileReport` with collected statistics.
        """
        self._process()

        return FileReport(statistics=self.stats, filepath=self.relative_path)
