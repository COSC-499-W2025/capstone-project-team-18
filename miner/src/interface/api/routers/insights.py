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

from src.core.insight.insight_generator import (
    ActivityInsightCalculator,
    InsightCalculator,
    InsightGenerator,
    OwnershipInsightCalculator,
    SkillsInsightCalculator,
)
from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.database.api.CRUD.insights import (
    dismiss_project_insight,
    get_dismissed_insight_messages,
    get_project_insights,
    save_project_insights,
)
from src.database.api.CRUD.projects import get_project_report_by_name
from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.utils.errors import ProjectNotFoundError

router = APIRouter(
    prefix="/projects",
    tags=["insights"],
)

logger = get_logger(__name__)


NON_ML_INSIGHT_CALCULATORS: list[type[InsightCalculator]] = [
    ActivityInsightCalculator,
    OwnershipInsightCalculator,
    SkillsInsightCalculator,
]


class InsightResponse(BaseModel):
    message: str


class ProjectInsightsResponse(BaseModel):
    project_name: str
    insights: list[InsightResponse]


class DismissInsightRequest(BaseModel):
    message: str


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

    ml_allowed = ml_extraction_allowed(session=session)

    # Cached insight rows do not track whether messages were ML-derived.
    # When ML is currently disallowed, bypass cache and regenerate only the
    # non-ML subset so previously cached ML-derived prompts are not returned.
    dismissed = get_dismissed_insight_messages(session, decoded_name)

    cached = get_project_insights(session, decoded_name)
    if cached is not None and ml_allowed:
        active = [m for m in cached.insights if m not in dismissed]
        return ProjectInsightsResponse(
            project_name=decoded_name,
            insights=[InsightResponse(message=m) for m in active],
        )

    report = get_project_report_by_name(session, decoded_name)
    if report is None:
        raise ProjectNotFoundError(f"Project '{decoded_name}' not found.")

    try:
        requested_classes = None if ml_allowed else NON_ML_INSIGHT_CALCULATORS
        insights = InsightGenerator.generate(
            report, requested_classes=requested_classes)
    except Exception:
        logger.exception(
            "Error generating insights for project '%s'", decoded_name)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate insights.",
        )

    messages = [i.message for i in insights]

    # Save only when ML-derived insights are currently allowed. The cache does
    # not record per-message source metadata, so persisting filtered non-ML
    # results here would overwrite a fuller cache generated under consent.
    if ml_allowed:
        save_project_insights(session, decoded_name, messages)
        session.commit()

    active_messages = [m for m in messages if m not in dismissed]
    return ProjectInsightsResponse(
        project_name=decoded_name,
        insights=[InsightResponse(message=m) for m in active_messages],
    )


@router.post("/{project_name}/insights/dismiss")
def dismiss_project_insight_endpoint(
    project_name: str,
    request: DismissInsightRequest,
    session: Session = Depends(get_session),
):
    """
    Dismiss an insight message for a project so it is never returned again.

    Path parameters:
    - `project_name`: The URL-encoded name of the project.

    Body:
    - `message`: The exact insight message text to dismiss.

    Returns:
    - 200: `{"dismissed": true}`

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    """
    decoded_name = unquote(project_name)

    report = get_project_report_by_name(session, decoded_name)
    if report is None:
        raise ProjectNotFoundError(f"Project '{decoded_name}' not found.")

    dismiss_project_insight(session, decoded_name, request.message)
    session.commit()

    return {"dismissed": True}
