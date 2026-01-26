"""
This file makes importing the ORM classes for our tables much
easier. Instead of

from src.database.models.file_report_table import FileReportTable

We can instead import the table with

from src.database.models import FileReportTable
"""

from .file_report_table import FileReportTable
from .project_report_table import ProjectReportTable
from .user_report_table import UserReportTable
from .proj_user_assoc_table import proj_user_assoc_table
from .resume_table import Resume
from .resume_item_table import ResumeItemTable
from .portfolio_table import PortfolioTable

__all__ = [
    "FileReportTable",
    "ProjectReportTable",
    "UserReportTable",
    "proj_user_assoc_table",
    "Resume",
    "ResumeItemTable",
    "PortfolioTable",
]
