from sqlmodel import Session, select
from typing import Optional
from sqlmodel import Session
from src.database.api.models import ProjectReportModel
from src.core.report import ProjectReport
from src.database.core.model_serializer import serialize_project_report, serialize_file_report
from src.database.core.model_deserializer import deserialize_project_report


def save_project_report(
    session: Session,
    project_report: ProjectReport,
    user_config_id: Optional[int]
) -> ProjectReportModel:
    """
    Save a ProjectReport domain object along with all its FileReports
    and generated ProjectBlocks into the database. DOES NOT COMMIT THE
    SESSION! YOU MUST COMMIT.

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

    return project_model


def get_project_report_model_by_name(
        session: Session,
        project_name: str
) -> Optional[ProjectReportModel]:
    statement = select(ProjectReportModel).where(
        ProjectReportModel.project_name == project_name)
    return session.exec(statement).first()


def get_project_report_by_name(
    session: Session,
    project_name: str
) -> Optional[ProjectReport]:
    """
    Retrieve a ProjectReportModel by its project_name, including
    related FileReports and ProjectBlocks.

    Args:
        session: SQLModel Session
        project_name: The project name to query

    Returns:
        ProjectReportModel if found, else None
    """
    result = get_project_report_model_by_name(session, project_name)

    if result is None:
        return None

    return deserialize_project_report(result)


def delete_project_report_by_name(
    session: Session,
    project_name: str
) -> bool:
    """
    Delete a ProjectReportModel by its project_name. DOES NOT COMMIT THE
    SESSION! YOU MUST COMMIT.

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
    return True
