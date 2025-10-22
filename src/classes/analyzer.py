"""
This file holds all the Analyzer classes. These are classes will analyze
a file and generate a report with statistics.
"""
from .report import FileReport
from .statistic import Statistic, StatisticIndex, FileStatCollection
import datetime
from pathlib import Path
import logging
logger = logging.basicConfig(level=logging.DEBUG)


class BaseFileAnalyzer:
    """
    Base class for file analysis. Provides a framework for collecting
    file-level statistics.

    To analyze a specific file, extend this class and implement the
    _process method. In this method, call the _process method of the
    superclass to collect basic statistics, then add any file-specific
    statistics to the StatisticIndex (self.stats).
    to the StatisticIndex (self.stats).

    Attributes:
        filepath (str): The path to the file being analyzed.
        stats (StatisticIndex): The index holding collected statistics.

    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.stats = StatisticIndex()

    def _process(self) -> None:
        """
        A private function that collects basic statistics available for any file.
        This includes a file's:
        - Creation date
        - Last modified/accessed date
        - Size (in bytes)

        All of the metadata is wrapped into a list and put into `self.stats`.
        """
        try:
            metadata = Path(self.filepath).stat()

            created = datetime.datetime.fromtimestamp(
                getattr(metadata, 'st_birthtime', metadata.st_ctime))
            last_accessed = datetime.datetime.fromtimestamp(metadata.st_atime)
            last_modified = datetime.datetime.fromtimestamp(metadata.st_mtime)
            size_bytes = metadata.st_size

            stats = [
                Statistic(FileStatCollection.DATE_CREATED.value, created),
                Statistic(FileStatCollection.DATE_ACCESSED.value,
                          last_accessed),
                Statistic(FileStatCollection.DATE_MODIFIED.value,
                          last_modified),
                Statistic(FileStatCollection.FILE_SIZE_BYTES.value, size_bytes)
            ]
            self.stats.add_list(stats)
        except (FileNotFoundError, PermissionError, OSError, AttributeError) as e:
            logging.error(
                f"Couldn't access metadata for a file in: {self.filepath}. \nError thrown: {str(e)}")

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a FileReport with collected statistics.
        """
        self._process()

        return FileReport(statistics=self.stats, filepath=self.filepath)

    def extract_file_reports(project_title: str, project_structure: dict) -> list[FileReport]:
        """
        Method to extract inidvidual fileReports within each project
        """
        # Given a single project for a user and the project's structure return a list with each fileReport
        projectFiles = project_structure[project_title]

        # empty list to be returned
        reports = []

        for file in projectFiles:
            analyzer = BaseFileAnalyzer(file)
            reports.append(analyzer.analyze())

        return reports


class TextFileAnalyzer(BaseFileAnalyzer):
    """
    Analyzer for plain text files. Extends BaseFileAnalyzer with
    text-specific metrics (e.g., line count, word count).
    """

    def _process(self) -> None:
        super()._process()

        raise ValueError("Unimplemented")

        # Example: count lines (mocked here)
        self.stats.add(Statistic(FileStatTemplate.LINES_IN_FILE, 30))
