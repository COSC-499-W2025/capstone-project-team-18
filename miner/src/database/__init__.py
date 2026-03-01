"""
The db package has everything that is needed for the database.
"""

from .api.CRUD.projects import save_project_report, get_project_report_by_name, delete_project_report_by_name, get_project_report_model_by_name
from .api.CRUD.resume import save_resume, load_resume, get_resume_model_by_id

from .api.CRUD.user_config import get_most_recent_user_config, save_user_config
from .api.CRUD.portfolio import get_portfolio_block, load_portfolio, save_portfolio, update_portfolio_block

from .api.models import UserConfigModel, ProjectReportModel, FileReportModel, ResumeItemModel, ResumeModel, PortfolioModel

from .core.base import get_engine

__all__ = [
    "save_project_report",
    "get_project_report_by_name",
    "get_project_report_model_by_name",
    "delete_project_report_by_name",
    "get_most_recent_user_config",
    "save_user_config",
    "get_portfolio_block",
    "load_portfolio",
    "save_portfolio",
    "update_portfolio_block",

    "UserConfigModel",
    "ProjectReportModel",
    "FileReportModel",
    "ResumeItemModel",
    "ResumeModel",
    "PortfolioModel",

    # Resume CRUD
    "save_resume",
    "load_resume",
    "get_resume_model_by_id",

    "get_engine"
]
