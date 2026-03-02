from datetime import datetime
from sqlmodel import Session, select
from typing import Optional, List
from sqlmodel import Session
from src.database.api.models import ProjectReportModel, FileReportModel
from src.core.report import ProjectReport
from src.database.core.model_serializer import serialize_project_report, serialize_file_report
from src.database.core.model_deserializer import deserialize_project_report


def _get_latest_related_project_model(
    session: Session,
    base_project_name: str
) -> Optional[ProjectReportModel]:
    """
    Get the latest saved project in a version chain.

    A related project is either:
    - Exact base name (e.g. "ProjectA")
    - Versioned name (e.g. "ProjectA_2", "ProjectA_3", ...)
    """
    statement = select(ProjectReportModel).where(
        (ProjectReportModel.project_name == base_project_name) |
        (ProjectReportModel.project_name.like(f"{base_project_name}_%"))
    )
    related_projects = session.exec(statement).all()

    if not related_projects:
        return None

    return max(
        related_projects,
        key=lambda project: (
            project.analyzed_count if project.analyzed_count is not None else 1,
            project.created_at
        )
    )


def get_latest_related_project_report(
    session: Session,
    base_project_name: str
) -> Optional[ProjectReport]:
    """
    Retrieve the latest saved ProjectReport in a version chain by base project name.

    Args:
        session: SQLModel Session
        base_project_name: Unversioned project name (e.g. "ProjectA")

    Returns:
        Latest related ProjectReport if found, else None
    """
    latest_model = _get_latest_related_project_model(
        session, base_project_name)

    if latest_model is None:
        return None

    return deserialize_project_report(latest_model)


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
    latest_related_project = _get_latest_related_project_model(
        session=session,
        base_project_name=project_report.project_name
    )

    if existing is None and latest_related_project is None:
        incoming_model.file_reports = incoming_files
        session.add(incoming_model)
        return incoming_model

    existing = existing or latest_related_project
    previous_project_name = existing.project_name

    if latest_related_project is not None:
        next_count = (latest_related_project.analyzed_count or 1) + 1
        existing.project_name = f"{project_report.project_name}_{next_count}"
        existing.analyzed_count = next_count
        existing.parent = previous_project_name
    else:
        existing.project_name = project_report.project_name
        existing.analyzed_count = 1
        existing.parent = None

    # Upsert behavior: refresh existing project row and replace child file rows.
    # This prevents UNIQUE(project_name) crashes on repeated analyses.
    existing.user_config_used = user_config_id
    existing.statistic = incoming_model.statistic
    existing.last_updated = datetime.now()

    stale_files = session.exec(
        select(FileReportModel).where(
            FileReportModel.project_name == previous_project_name)
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


def get_all_project_report_models(session: Session) -> List[ProjectReportModel]:
    """
    Retrieve all ProjectReportModel records from the database.

    Args:
        session: SQLModel Session

    Returns:
        A list of ProjectReportModel instances.
    """
    statement = select(ProjectReportModel)
    return list(session.exec(statement).all())
