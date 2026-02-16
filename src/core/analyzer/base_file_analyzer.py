import datetime
from pathlib import Path
from sqlmodel import Session
from git import GitCommandError
import hashlib

# database imports are needed for duplicate files checks
from src.core.statistic.statistic_models import LANGUAGE_EXTENSIONS
from src.database.api.CRUD.files import get_file_report_model_by_hash


from src.core.report.file_report import FileReport
from src.database.api.models import UserConfigModel as UserConfig
from src.core.project_discovery.project_discovery import ProjectLayout
from src.core.statistic import Statistic, StatisticIndex, FileStatCollection
from src.infrastructure.log.logging import get_logger
from src.database.core.base import get_engine
from datetime import date

logger = get_logger(__name__)

user_config: UserConfig
project_context: ProjectLayout


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

    def __init__(self, user_config: UserConfig, project_context: ProjectLayout, relative_path: str):

        self.path_to_top_level_project = str(project_context.root_path)
        self.relative_path = relative_path
        self.filepath = f"{self.path_to_top_level_project}/{relative_path}"
        self.created_at = self.get_created_time()

        self.project_name = project_context.name
        self.repo = project_context.repo

        self.email = user_config.user_email
        self.github = user_config.github

        self.stats = StatisticIndex()
        self.blame_info = None
        self.is_git_tracked = self.file_in_git_repo()
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

    def create_info_file(self) -> FileReport:
        """
        This is a method that is used to create a fileReport object with no stats and only
        a bool denoting whether it has been contributed to

        Returns:
            fileReport: Only runs in the case of should_analyze_file() -> False.
        """

        stats = []
        self.stats.extend(stats)

        return FileReport(statistics=self.stats,
                          filepath=self.relative_path,
                          file_hash=b"",
                          project_name=self.project_name,
                          is_info_file=True)

    def should_analyze_file(self) -> bool:
        """
        This is a lightweight check to see if the file should be
        included in analysis. By default, all files are included.

        A file is excluded if it meets certain criteria:
            - If the user has configured to exclude files of this type
            - If user has given their email, and the file is tracked by git,
                but none of the lines in the file were authored by the user.

        Returns:
            bool: True if the file should be included, False otherwise.
        """

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

    def get_created_time(self) -> date:
        """By opening the file to create the hash, we corrupt the `created_at` time.
        To resolve this, we get and store the time prior to hashing
        """
        metadata = Path(self.filepath).stat()
        return datetime.datetime.fromtimestamp(
            metadata.st_atime)

    def create_hash(self) -> bytes:
        """
        Create a hash of the file's content. Should only occur in the case of a new file, or
        in the case of a matching existing path in order to check against hash value

        Returns:
            bytes: A hex representation of the resulting MD5 hash
        """
        try:
            with open(self.filepath, "rb") as f:
                hashed_file = hashlib.file_digest(f, "md5")

            # unchanged file with changed email will still result in re-analysis
            if self.email:
                salt = self.email.encode('utf-8')
            else:
                salt = b'0'
            hash = hashed_file.digest() + salt
            return hash
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
            return (
                get_file_report_model_by_hash(
                    session, self.hashed_content) is not None
            )

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
                      metadata.st_size)
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

            stats.append(
                Statistic(FileStatCollection.DATE_CREATED.value, self.created_at))
            stats.append(Statistic(FileStatCollection.DATE_MODIFIED.value, datetime.datetime.fromtimestamp(
                metadata.st_mtime)))

        self.stats.extend(stats)

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a `FileReport` with collected statistics.
        """
        self._process()

        return FileReport(statistics=self.stats,
                          filepath=self.relative_path,
                          file_hash=b"",
                          project_name=self.project_name,
                          is_info_file=False)
