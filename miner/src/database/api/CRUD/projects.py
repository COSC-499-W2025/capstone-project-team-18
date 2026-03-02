from sqlmodel import Session, select
from typing import Optional
from src.database.api.models import ProjectReportModel
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
    latest_model = _get_latest_related_project_model(session, base_project_name)

    if latest_model is None:
        return None

    return deserialize_project_report(latest_model)


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

    project_model = serialize_project_report(project_report, user_config_id)

    latest_related_project = _get_latest_related_project_model(
        session=session,
        base_project_name=project_report.project_name
    )

    if latest_related_project is not None:
        next_count = (latest_related_project.analyzed_count or 1) + 1
        project_model.project_name = f"{project_report.project_name}_{next_count}"
        project_model.analyzed_count = next_count
        project_model.parent = latest_related_project.project_name
    else:
        project_model.project_name = project_report.project_name
        project_model.analyzed_count = 1
        project_model.parent = None

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
