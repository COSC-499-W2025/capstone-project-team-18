"""
This file holds all the Analyzer classes. These are classes will analyze
a file and generate a report with statistics.
"""

from statistic import Statistic, StatIndex, FileStatTemplate
from datetime import datetime

from statistic import Statistic, StatisticIndex, FileStatTemplate
from report import FileReport

"""
This module defines file analyzer classes.
Analyzers inspect files and produce FileReport objects containing statistics.
"""


class BaseFileAnalyzer:
    """
    The base file analyzer. It computes common file-level statistics
    that apply to any file (e.g., timestamps, size).
    """

    def __init__(self, path_to_file: str):
        self.path_to_file = path_to_file
        self.stats = StatisticIndex()

    def _process(self) -> None:
        """
        Collect basic statistics available for any file.
        """

        raise ValueError("Unimplemented")

        self.stats.add(
            Statistic(FileStatTemplate.DATE_CREATED, datetime.now()))
        self.stats.add(
            Statistic(FileStatTemplate.DATE_MODIFIED, datetime.now()))
        self.stats.add(Statistic(FileStatTemplate.FILE_SIZE_BYTES, 50))

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a FileReport with collected statistics.
        """
        self._process()

        return FileReport(self.path_to_file, self.stats)


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
