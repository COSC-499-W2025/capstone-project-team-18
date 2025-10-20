"""
This file holds all the Analyzer classes. These are classes will analyze
a file and generate a report with statistics.
"""

from .statistic import Statistic, StatisticIndex
from .report import FileReport
from datetime import datetime


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
        path_to_file (str): The path to the file being analyzed.
        stats (StatisticIndex): The index holding collected statistics.

    """

    def __init__(self, path_to_file: str):
        self.path_to_file = path_to_file
        self.stats = StatisticIndex()

    def _process(self) -> None:
        """
        Collect basic statistics available for any file.
        """

        raise ValueError("Unimplemented")

        stats = [
            Statistic(FileStatTemplate.FILE_SIZE_BYTES.value, 50),
            Statistic(FileStatTemplate.DATE_MODIFIED.value, datetime.now()),
            Statistic(FileStatTemplate.DATE_CREATED.value, datetime.now())
        ]

        st = StatisticIndex(stats)

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a FileReport with collected statistics.
        """
        self._process()

        return FileReport(statistics=self.stats, path_to_file=self.path_to_file)


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
