"""
GET /projects/{project_name}/insights

Returns a list of insight prompts derived from an existing ProjectReport.
Insights help users reflect on their contributions when writing a resume.
"""

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from src.core.insight.insight_generator import InsightGenerator
from src.database.api.CRUD.projects import get_project_report_by_name
from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session

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
def get_project_insights(
    project_name: str,
    session: Session = Depends(get_session),
):
    """
    Return a list of resume-writing insight prompts for the given project.

    Insights are derived at request time from already-mined statistics — no
    new mining or database writes occur.
    """
    decoded_name = unquote(project_name)

    report = get_project_report_by_name(session, decoded_name)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{decoded_name}' not found.",
        )

    try:
        insights = InsightGenerator.generate(report)
    except Exception:
        logger.exception("Error generating insights for project '%s'", decoded_name)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate insights.",
        )

    return ProjectInsightsResponse(
        project_name=decoded_name,
        insights=[InsightResponse(message=i.message) for i in insights],
    )
