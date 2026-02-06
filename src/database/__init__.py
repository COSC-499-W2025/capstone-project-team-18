"""
The db package has everything that is needed for the database.
"""

from .api.CRUD.projects import save_project_report, get_project_report_by_name, delete_project_report_by_name
from .api.CRUD.user_config import get_most_recent_user_config, save_user_config

from .api.models import UserConfigModel, ProjectReportModel, FileReportModel, ResumeItemModel, ResumeModel

__all__ = [
    "save_project_report",
    "get_project_report_by_name",
    "delete_project_report_by_name",
    "get_most_recent_user_config",
    "save_user_config",

    "UserConfigModel",
    "ProjectReportModel",
    "FileReportModel",
    "ResumeItemModel",
    "ResumeModel"
]
