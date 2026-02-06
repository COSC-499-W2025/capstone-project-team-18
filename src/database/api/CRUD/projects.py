from sqlmodel import Session, select
from typing import Optional
from sqlmodel import Session
from src.database.api.models import ProjectReportModel
from src.core.report import ProjectReport
from src.database.core.model_seralizer import serialize_project_report, serialize_file_report
from src.database.core.model_deseralizer import deseralize_project_report


def save_project_report(
    session: Session,
    project_report: ProjectReport,
    user_config_id: Optional[int]
) -> ProjectReportModel:
    """
    Save a ProjectReport domain object along with all its FileReports
    and generated ResumeItems into the database.

    Args:
        session: SQLModel Session
        project_report: ProjectReport domain object
        user_config_id: ID of the associated UserConfigModel

    Returns:
        The saved ProjectReportModel instance
    """

    project_model = serialize_project_report(project_report, user_config_id)

    file_models = [serialize_file_report(fr)
                   for fr in project_report.file_reports]
    project_model.file_reports = file_models

    session.add(project_model)
    session.commit()
    session.refresh(project_model)  # refresh to get updated relationships

    return project_model


def get_project_report_by_name(
    session: Session,
    project_name: str
) -> Optional[ProjectReport]:
    """
    Retrieve a ProjectReportModel by its project_name, including
    related FileReports and ResumeItems.

    Args:
        session: SQLModel Session
        project_name: The project name to query

    Returns:
        ProjectReportModel if found, else None
    """
    statement = select(ProjectReportModel).where(
        ProjectReportModel.project_name == project_name
    )

    result = session.exec(statement).first()

    if result is None:
        return None

    return deseralize_project_report(result)


def delete_project_report_by_name(
    session: Session,
    project_name: str
) -> bool:
    """
    Delete a ProjectReportModel by its project_name.

    Args:
        session: SQLModel Session
        project_name: The project name to delete

    Returns:
        True if a record was deleted, False if not found.
    """
    statement = select(ProjectReportModel).where(
        ProjectReportModel.project_name == project_name
    )

    project = session.exec(statement).first()

    if project is None:
        return False

    session.delete(project)
    session.commit()
    return True
