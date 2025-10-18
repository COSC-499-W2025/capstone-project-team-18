"""
This file holds all the Analyzer classes. These are classes will analyze
a file and generate a report with statistics.
"""
import datetime
from pathlib import Path

from .statistic import Statistic, StatisticIndex, FileStatCollection
from report import FileReport


class BaseFileAnalyzer:
    """
    Base class for file analysis. Provides a framework for collecting
    file-level statistics.

    To be a specific file analyzer, extend this class and implement the
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

        Returns:
        -
        """
        metadata = Path(self.filepath).stat()

        # file's creation date
        created = datetime.datetime.fromtimestamp(
            getattr(metadata, 'st_birthtime', metadata.st_ctime))

        # file's last accessed/modified date
        modified = datetime.datetime.fromtimestamp(metadata.st_atime)

        size_bytes = metadata.st_size

        stats = [
            Statistic(
                FileStatCollection.DATE_CREATED.value, created),
            Statistic(
                FileStatCollection.DATE_MODIFIED.value, modified),
            Statistic(
                FileStatCollection.FILE_SIZE_BYTES.value, size_bytes)
        ]
        self.stats.add_list(stats)

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a FileReport with collected statistics.
        """
        self._process()

        return FileReport(statistics=self.stats, filepath=self.filepath)


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
