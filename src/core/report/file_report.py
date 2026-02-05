"""
This file defines the FileReport class
"""

from pathlib import Path
from typing import Optional

from src.core.report.base_report import BaseReport
from src.core.statistic import StatisticIndex


class FileReport(BaseReport):
    """
    The `FileReport` class is the lowest level report. It is made
    by file-type-specific analyzers.
    """

    filepath: str

    # Optional iff. we are not storing it in the database (testing purposes)
    is_info_file: Optional[bool]
    file_hash: Optional[bytes]
    project_name: Optional[str]

    def __init__(self,
                 statistics: StatisticIndex,
                 filepath: str,
                 is_info_file: Optional[bool] = None,
                 file_hash: Optional[bytes] = None,
                 project_name: Optional[str] = None):

        super().__init__(statistics)
        self.filepath = filepath
        self.is_info_file = is_info_file
        self.file_hash = file_hash
        self.project_name = project_name

    def get_filename(self):
        return Path(self.filepath).name
