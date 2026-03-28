from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

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


def _dedupe_messages(messages: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for message in messages:
        cleaned = str(message or '').strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped


def _filter_feedback(messages: list[str], current_insights: list[str]) -> list[str]:
    active_messages = set(current_insights)
    return [message for message in _dedupe_messages(messages) if message in active_messages]


def save_project_insights(
    session: Session,
    project_name: str,
    insight_messages: list[str],
) -> ProjectInsightsModel:
    """
    Persist insight messages for a project.

    If a row already exists it is replaced; otherwise a new row is inserted.
    Existing feedback is preserved only for insight messages that still exist.
    """

    normalized_messages = _dedupe_messages(insight_messages)
    pi = get_project_insights(session, project_name)

    if pi is not None:
        pi.insights = normalized_messages
        pi.useful_insights = _filter_feedback(pi.useful_insights, normalized_messages)
        pi.dismissed_insights = _filter_feedback(pi.dismissed_insights, normalized_messages)
        pi.generated_at = datetime.now()
        session.add(pi)
    else:
        pi = ProjectInsightsModel(
            project_name=project_name,
            insights=normalized_messages,
        )

        session.add(pi)

    return pi


def update_project_insight_feedback(
    session: Session,
    project_name: str,
    message: str,
    useful: bool | None = None,
    dismissed: bool | None = None,
) -> Optional[ProjectInsightsModel]:
    """Persist useful/dismissed feedback for one cached insight message."""

    insight_row = get_project_insights(session, project_name)
    if insight_row is None:
        return None

    normalized_message = str(message or '').strip()
    if normalized_message not in insight_row.insights:
        raise ValueError('Insight message was not found for the project.')

    useful_messages = set(_dedupe_messages(insight_row.useful_insights))
    dismissed_messages = set(_dedupe_messages(insight_row.dismissed_insights))

    if useful is not None:
        (useful_messages.add if useful else useful_messages.discard)(normalized_message)

    if dismissed is not None:
        (dismissed_messages.add if dismissed else dismissed_messages.discard)(normalized_message)

    insight_row.useful_insights = [msg for msg in insight_row.insights if msg in useful_messages]
    insight_row.dismissed_insights = [msg for msg in insight_row.insights if msg in dismissed_messages]
    session.add(insight_row)
    return insight_row
