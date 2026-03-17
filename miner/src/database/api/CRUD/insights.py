from typing import Optional
from sqlmodel import Session, select
from datetime import datetime

from src.database.api.models import ProjectInsightsModel


def get_project_insights(
    session: Session,
    project_name: str,
) -> Optional[ProjectInsightsModel]:
    """Return the cached ProjectInsightsModel for a project, or None."""
    return session.exec(
        select(ProjectInsightsModel).where(
            ProjectInsightsModel.project_name == project_name
        )
    ).first()


def save_project_insights(
    session: Session,
    project_name: str,
    insight_messages: list[str],
) -> ProjectInsightsModel:
    """
    Persist insight messages for a project.

    If a row already exists it is replaced; otherwise a new row is inserted.
    """

    pi = get_project_insights(session, project_name)

    if pi is not None:
        pi.insights = insight_messages
        pi.generated_at = datetime.now()
        session.add(pi)
    else:
        pi = ProjectInsightsModel(
            project_name=project_name,
            insights=insight_messages,
        )

        session.add(pi)

    return pi
