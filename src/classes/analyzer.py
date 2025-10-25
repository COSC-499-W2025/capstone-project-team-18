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

            # Map file statistic templates to their corresponding timestamp values
            timestamps = {
                FileStatCollection.DATE_CREATED.value: getattr(metadata, "st_birthtime", metadata.st_ctime),
                FileStatCollection.DATE_ACCESSED.value: metadata.st_atime,
                FileStatCollection.DATE_MODIFIED.value: metadata.st_mtime,
            }

            # Add timestamp stats
            for template, value in timestamps.items():
                self.stats.add(
                    Statistic(template, datetime.datetime.fromtimestamp(value)))

            self.stats.add(
                Statistic(FileStatCollection.FILE_SIZE_BYTES.value, metadata.st_size))

        except (FileNotFoundError, PermissionError, OSError, AttributeError) as e:
            logging.error(
                f"Couldn't access metadata for a file in: {self.filepath}. \nError thrown: {str(e)}")

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
