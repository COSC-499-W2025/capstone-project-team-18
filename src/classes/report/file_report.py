"""
This file defines the FileReport class
"""

from pathlib import Path

from src.classes.report.base_report import BaseReport
from src.classes.statistic import StatisticIndex


class FileReport(BaseReport):
    """
    The `FileReport` class is the lowest level report. It is made
    by file-type-specific analyzers.
    """

    filepath: str

    def __init__(self, statistics: StatisticIndex, filepath: str):
        super().__init__(statistics)
        self.filepath = filepath

    @classmethod
    def create_with_analysis(cls, path_to_top_level: str, relative_path: str) -> "FileReport":
        """
        Create a `FileReport` with automatic file type detection and analysis.
        This includes:
                - Base statistics (e.g., date created)
                - Natural Language statistics for appropriate langauge based files (e.g., .docx, word count stat)
                - Statistics applicable to all coding langauges (e.g., type of file)
                - Statistics specific to a coding language (e.g., number of classes for a python file)
        """
        from src.classes.analyzer import get_appropriate_analyzer
        analyzer = get_appropriate_analyzer(path_to_top_level, relative_path)
        return analyzer.analyze()

    def get_filename(self):
        return Path(self.filepath).name
