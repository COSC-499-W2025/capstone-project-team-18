"""
This file acts as a central hub for everything report.
This makes it so we can just use

`from src.core.report import FileReport, ProjectReport`

instead of

`from src.core.analyzer.file_report import FileReport`
`from src.core.analyzer.project_report import ProjectReport`

This makes things a little cleaner.
"""

from .base_report import BaseReport
from .file_report import FileReport
from .project.project_report import ProjectReport
from .user.user_report import UserReport

__all__ = [
    "BaseReport",
    "FileReport",
    "ProjectReport",
    "UserReport"
]
