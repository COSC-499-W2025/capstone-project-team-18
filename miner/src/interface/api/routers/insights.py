"""
GET /projects/{project_name}/insights

Returns a list of insight prompts derived from an existing ProjectReport.
Insights help users reflect on their contributions when writing a resume.

Insights are cached in the database after the first generation so that
expensive or ML-based generators are only invoked once per project.
"""

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
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
    get_project_insights,
    save_project_insights,
    update_project_insight_feedback,
)
from src.database.api.CRUD.projects import get_project_report_by_name
from src.database.api.models import ProjectInsightsModel
from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.services.project_insight_service import generate_project_insight_replacements
from src.utils.errors import ProjectNotFoundError

router = APIRouter(
    prefix="/projects",
    tags=["insights"],
)

logger = get_logger(__name__)
MIN_VISIBLE_INSIGHTS = 5
MAX_CACHED_INSIGHTS = 10


NON_ML_INSIGHT_CALCULATORS: list[type[InsightCalculator]] = [
    ActivityInsightCalculator,
    OwnershipInsightCalculator,
    SkillsInsightCalculator,
]


class InsightResponse(BaseModel):
    message: str
    useful: bool = False
    dismissed: bool = False


class ProjectInsightsResponse(BaseModel):
    project_name: str
    insights: list[InsightResponse]


class InsightFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    useful: bool | None = None
    dismissed: bool | None = None


def _serialize_insights(project_name: str, cached: ProjectInsightsModel | None, messages: list[str]) -> ProjectInsightsResponse:
    useful_messages = set(cached.useful_insights if cached is not None else [])
    dismissed_messages = set(cached.dismissed_insights if cached is not None else [])
    return ProjectInsightsResponse(
        project_name=project_name,
        insights=[
            InsightResponse(
                message=message,
                useful=message in useful_messages,
                dismissed=message in dismissed_messages,
            )
            for message in messages
        ],
    )


def _undismissed_count(cached: ProjectInsightsModel) -> int:
    dismissed = set(cached.dismissed_insights)
    return len([message for message in cached.insights if message not in dismissed])


def _refill_cached_insights_if_needed(
    session: Session,
    project_name: str,
    report,
    cached: ProjectInsightsModel,
    allow_azure: bool,
) -> ProjectInsightsModel:
    remaining_capacity = max(0, MAX_CACHED_INSIGHTS - len(cached.insights))
    needed = min(max(0, MIN_VISIBLE_INSIGHTS - _undismissed_count(cached)), remaining_capacity)
    if needed == 0:
        return cached

    additions = generate_project_insight_replacements(
        report=report,
        existing_insights=cached.insights,
        dismissed_insights=cached.dismissed_insights,
        count=needed,
        allow_azure=allow_azure,
    )
    if not additions:
        return cached

    return save_project_insights(session, project_name, cached.insights + additions)


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
    cached = get_project_insights(session, decoded_name)

    if cached is not None and ml_allowed and _undismissed_count(cached) >= MIN_VISIBLE_INSIGHTS:
        return _serialize_insights(decoded_name, cached, cached.insights)

    report = get_project_report_by_name(session, decoded_name)
    if report is None:
        raise ProjectNotFoundError(f"Project '{decoded_name}' not found.")

    if cached is not None and ml_allowed:
        cached = _refill_cached_insights_if_needed(
            session=session,
            project_name=decoded_name,
            report=report,
            cached=cached,
            allow_azure=ml_allowed,
        )
        session.commit()
        session.refresh(cached)
        return _serialize_insights(decoded_name, cached, cached.insights)

    try:
        requested_classes = None if ml_allowed else NON_ML_INSIGHT_CALCULATORS
        insights = InsightGenerator.generate(
            report,
            requested_classes=requested_classes,
        )
    except Exception:
        logger.exception(
            "Error generating insights for project '%s'", decoded_name)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate insights.",
        )

    messages = [i.message for i in insights]
    if len(messages) < MIN_VISIBLE_INSIGHTS:
        messages.extend(
            generate_project_insight_replacements(
                report=report,
                existing_insights=messages,
                dismissed_insights=[],
                count=min(MIN_VISIBLE_INSIGHTS - len(messages), MAX_CACHED_INSIGHTS - len(messages)),
                allow_azure=ml_allowed,
            )
        )

    cached_result = None
    if ml_allowed:
        cached_result = save_project_insights(session, decoded_name, messages)
        session.commit()

    return _serialize_insights(decoded_name, cached_result, messages)


@router.patch("/{project_name}/insights/feedback", response_model=ProjectInsightsResponse)
def update_project_insights_feedback_endpoint(
    project_name: str,
    request: InsightFeedbackRequest,
    session: Session = Depends(get_session),
):
    """
    Update persisted useful/dismissed feedback for a cached project insight.

    Persists user feedback for one insight message. If the insight is dismissed,
    the backend will refill the cached pool so the UI can continue showing the
    minimum visible insight count.

    Path parameters:
    - `project_name`: The URL-encoded name of the project.

    Body parameters:
    - `message`: The exact insight message being updated.
    - `useful`: Optional boolean to mark or unmark the insight as useful.
    - `dismissed`: Optional boolean to mark or unmark the insight as dismissed.

    Returns:
    - 200: A `ProjectInsightsResponse` containing the updated cached insight state.

    Raises:
    - 400: No feedback field was provided, or the insight message was not found.
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 409: Project insights have not been generated yet for the project.
    """
    decoded_name = unquote(project_name)
    report = get_project_report_by_name(session, decoded_name)

    if report is None:
        raise ProjectNotFoundError(f"Project '{decoded_name}' not found.")

    if request.useful is None and request.dismissed is None:
        raise HTTPException(
            status_code=400,
            detail="At least one feedback field must be provided.",
        )

    try:
        cached = update_project_insight_feedback(
            session,
            decoded_name,
            request.message,
            useful=request.useful,
            dismissed=request.dismissed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if cached is None:
        raise HTTPException(
            status_code=409,
            detail="Project insights must be generated before feedback can be updated.",
        )

    if request.dismissed:
        cached = _refill_cached_insights_if_needed(
            session=session,
            project_name=decoded_name,
            report=report,
            cached=cached,
            allow_azure=ml_extraction_allowed(session=session),
        )

    session.commit()
    session.refresh(cached)
    return _serialize_insights(decoded_name, cached, cached.insights)
