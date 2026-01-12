import datetime
from pathlib import Path
from typing import Optional
import logging
from git import GitCommandError, Repo

from src.classes.report.file_report import FileReport
from src.classes.statistic import Statistic, StatisticIndex, FileStatCollection, CodingLanguage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
                 language_filter: Optional[list[str]] = None
                 ):

        self.path_to_top_level_project = path_to_top_level_project
        self.relative_path = relative_path
        self.filepath = f"{path_to_top_level_project}/{relative_path}"
        self.repo = repo
        self.email = email
        self.language_filter = language_filter
        self.stats = StatisticIndex()
        self.blame_info = None
        self.is_git_tracked = self.file_in_git_repo()

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
            # Find matching CodingLanguage enum
            for coding_lang in CodingLanguage:
                # coding_lang.value is a tuple (name, [extensions])
                if coding_lang.value[0].lower() == lang_name.lower():
                    if file_ext in coding_lang.value[1]:
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
