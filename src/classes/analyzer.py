"""
This file holds all the Analyzer classes. These are classes will analyze
a file and generate a report with statistics.
"""

from statistic import Statistic
import datetime
from pathlib import Path


from .statistic import Statistic, StatisticIndex, FileStatisticTemplate, FileStatisticTemplateCollection
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
        path_to_file (str): The path to the file being analyzed.
        stats (StatisticIndex): The index holding collected statistics.

    """

    def __init__(self, path_to_file: str):
        self.path_to_file = path_to_file
        self.stats = StatisticIndex()

    def _process(self) -> None:
        """
        A private function that collects basic statistics available for any file.
        This includes the file's:
        - Creation date
        - Last modified/accessed date
        - Size (in bytes)
        """
        metadata = Path(self.path_to_file).stat()

        # file's creation date
        created = datetime.datetime.fromtimestamp(
            getattr(metadata, 'st_birthtime', metadata.st_ctime))

        # file's last accessed/modified date
        modified = datetime.datetime.fromtimestamp(metadata.st_atime)

        size_bytes = metadata.st_size

        stats = [
            Statistic(
                FileStatisticTemplateCollection.DATE_CREATED.value, created),
            Statistic(
                FileStatisticTemplateCollection.DATE_MODIFIED.value, modified),
            Statistic(
                FileStatisticTemplateCollection.FILE_SIZE_BYTES.value, size_bytes)
        ]
        self.stats.add_list(stats)

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
