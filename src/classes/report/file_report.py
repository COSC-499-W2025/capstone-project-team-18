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

    def get_filename(self):
        return Path(self.filepath).name
