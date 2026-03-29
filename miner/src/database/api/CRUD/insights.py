from typing import Optional
from sqlmodel import Session, select
from datetime import datetime

from src.database.api.models import DismissedInsightModel, ProjectInsightsModel


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


def get_dismissed_insight_messages(
    session: Session,
    project_name: str,
) -> set[str]:
    """Return the set of dismissed insight messages for a project."""
    rows = session.exec(
        select(DismissedInsightModel).where(
            DismissedInsightModel.project_name == project_name
        )
    ).all()
    return {row.message for row in rows}


def dismiss_project_insight(
    session: Session,
    project_name: str,
    message: str,
) -> DismissedInsightModel:
    """
    Record that the user dismissed an insight message for a project.

    If the same message has already been dismissed, returns the existing row
    without creating a duplicate.
    """
    existing = session.exec(
        select(DismissedInsightModel).where(
            DismissedInsightModel.project_name == project_name,
            DismissedInsightModel.message == message,
        )
    ).first()

    if existing is not None:
        return existing

    row = DismissedInsightModel(project_name=project_name, message=message)
    session.add(row)
    return row
