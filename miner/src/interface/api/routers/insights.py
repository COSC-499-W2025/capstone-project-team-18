"""
GET /projects/{project_name}/insights

Returns a list of insight prompts derived from an existing ProjectReport.
Insights help users reflect on their contributions when writing a resume.

Insights are cached in the database after the first generation so that
expensive or ML-based generators are only invoked once per project.
"""

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from src.core.insight.insight_generator import InsightGenerator
from src.database.api.CRUD.insights import get_project_insights, save_project_insights
from src.database.api.CRUD.projects import get_project_report_by_name
from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.utils.errors import ProjectNotFoundError

router = APIRouter(
    prefix="/projects",
    tags=["insights"],
)

logger = get_logger(__name__)


class InsightResponse(BaseModel):
    message: str


class ProjectInsightsResponse(BaseModel):
    project_name: str
    insights: list[InsightResponse]


@router.get("/{project_name}/insights", response_model=ProjectInsightsResponse)
def get_project_insights_endpoint(
    project_name: str,
    session: Session = Depends(get_session),
):
    """
    Return a list of resume-writing insight prompts for the given project.

    On the first call, insights are generated from the project's mined statistics
    and cached in the database. Subsequent calls return the cached copy.

    Path parameters:
    - `project_name`: The URL-encoded name of the project.

    Returns:
    - 200: A `ProjectInsightsResponse` with project_name and a list of insight messages.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500: Insight generation failed unexpectedly.
    """
    decoded_name = unquote(project_name)

    # Check to see if project insights are cached
    cached = get_project_insights(session, decoded_name)
    if cached is not None:
        return ProjectInsightsResponse(
            project_name=decoded_name,
            insights=[InsightResponse(message=m) for m in cached.insights],
        )

    # Else generate insights
    report = get_project_report_by_name(session, decoded_name)
    if report is None:
        raise ProjectNotFoundError(f"Project '{decoded_name}' not found.")

    try:
        insights = InsightGenerator.generate(report)
    except Exception:
        logger.exception(
            "Error generating insights for project '%s'", decoded_name)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate insights.",
        )

    messages = [i.message for i in insights]

    # Save the messages, if empty, that is okay, just means we have tried to
    # calulate the insights and we had nothing to say
    save_project_insights(session, decoded_name, messages)
    session.commit()

    return ProjectInsightsResponse(
        project_name=decoded_name,
        insights=[InsightResponse(message=m) for m in messages],
    )
