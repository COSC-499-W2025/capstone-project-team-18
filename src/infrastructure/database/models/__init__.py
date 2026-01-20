"""
This file makes importing the ORM classes for our tables much
easier. Instead of

from src.infrastructure.database.models.file_report_table import FileReportTable

We can instead import the table with

from src.infrastructure.database.models import FileReportTable
"""

from .file_report_table import FileReportTable
from .project_report_table import ProjectReportTable
from .user_report_table import UserReportTable
from .association_table import association_table

__all__ = [
    "FileReportTable",
    "ProjectReportTable",
    "UserReportTable",
    "association_table"
]
