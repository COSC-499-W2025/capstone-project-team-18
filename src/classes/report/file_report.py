"""
This file defines the FileReport class
"""

from pathlib import Path

from src.classes.report.base_report import BaseReport
from src.classes.statistic import StatisticIndex


class FileReport(BaseReport):
    """
    The FileReport class is the lowest level report. It is made
    by file-type specific, analyzers.
    """

    filepath: str

    def __init__(self, statistics: StatisticIndex, filepath: str):
        super().__init__(statistics)
        self.filepath = filepath

    @classmethod
    def create_with_analysis(cls, path_to_top_level: str, relative_path: str) -> "FileReport":
        """
        Create a FileReport with automatic file type detection and analysis.
        This includes:
                - Natural Language statistics for appropriate langauge based files
                - Python statistics for appropriate Python files
                - Java statistics for appropriate Java files
                - JavaScript statistics for appropriate JavaScript files
                - Text-based statistics for appropriate text based files (i.e. css, html, xml, json, yml, yaml)
        """
        from src.classes.analyzer import get_appropriate_analyzer
        analyzer = get_appropriate_analyzer(path_to_top_level, relative_path)
        return analyzer.analyze()

    def get_filename(self):
        return Path(self.filepath).name
