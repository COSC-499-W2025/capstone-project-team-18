from datetime import datetime
from sqlmodel import Session, select
from typing import Optional
from sqlmodel import Session
from src.database.api.models import ProjectReportModel, FileReportModel
from src.core.report import ProjectReport
from src.database.core.model_serializer import serialize_project_report, serialize_file_report
from src.database.core.model_deserializer import deserialize_project_report


def get_all_project_ids(
    session: Session
) -> list[str]:
    """
    Returns all the project report names
    """
    statement = select(ProjectReportModel.project_name)
    results = session.exec(statement).all()

    return list(results)


def save_project_report(
    session: Session,
    project_report: ProjectReport,
    user_config_id: Optional[int]
) -> ProjectReportModel:
    """
    Save a ProjectReport domain object along with all its FileReports
    and generated ResumeItems into the database. DOES NOT COMMIT THE
    SESSION! YOU MUST COMMIT.

    Args:
        session: SQLModel Session
        project_report: ProjectReport domain object
        user_config_id: ID of the associated UserConfigModel

    Returns:
        The saved ProjectReportModel instance
    """

    incoming_model = serialize_project_report(project_report, user_config_id)
    incoming_files = [serialize_file_report(
        fr) for fr in project_report.file_reports]

    existing = get_project_report_model_by_name(
        session, incoming_model.project_name)
    if existing is None:
        incoming_model.file_reports = incoming_files
        session.add(incoming_model)
        return incoming_model

    # Upsert behavior: refresh existing project row and replace child file rows.
    # This prevents UNIQUE(project_name) crashes on repeated analyses.
    existing.user_config_used = user_config_id
    existing.statistic = incoming_model.statistic
    existing.last_updated = datetime.now()

    stale_files = session.exec(
        select(FileReportModel).where(
            FileReportModel.project_name == existing.project_name)
    ).all()
    for row in stale_files:
        session.delete(row)

    for file_model in incoming_files:
        file_model.project_name = existing.project_name
        session.add(file_model)

    session.add(existing)
    return existing


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
    related FileReports and ResumeItems.

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
