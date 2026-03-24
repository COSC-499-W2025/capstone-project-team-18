from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Session

from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed
from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.services.job_readiness_service import (
    JobReadinessResult,
    JobReadinessUserProfileInput,
    build_user_profile,
    run_job_readiness_analysis,
)
from src.utils.errors import AIServiceUnavailableError

router = APIRouter(
    prefix="/job-readiness",
    tags=["job-readiness"],
)
logger = get_logger(__name__)


class JobReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_description: str = Field(min_length=1)
    resume_id: int | None = None
    project_names: list[str] = Field(default_factory=list)
    user_profile: JobReadinessUserProfileInput | None = None

    @field_validator("job_description")
    @classmethod
    def validate_job_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("job_description must contain non-whitespace characters")
        return stripped


@router.post("/analyze", response_model=JobReadinessResult)
def analyze_job_readiness(
    request: JobReadinessRequest,
    session: Session = Depends(get_session),
):
    """
    Analyze how well a candidate's profile matches a job description.

    Builds a candidate profile from optional resume and project evidence, then
    uses Azure OpenAI to score fit, list strengths and weaknesses, and produce
    prioritized improvement suggestions.

    Body parameters:
    - `job_description`: Required non-blank description of the target role.
    - `resume_id`: Optional resume record ID to include as evidence.
    - `project_names`: Optional list of project names to include as evidence.
    - `user_profile`: Optional manually supplied profile data.

    Returns:
    - 200: A `JobReadinessResult` with fit_score, summary, strengths, weaknesses,
      and suggestions.

    Raises:
    - 400: The supplied evidence is insufficient to run analysis.
    - 404: A requested project or resource was not found in the database.
    - 503 `AI_SERVICE_UNAVAILABLE`: Azure OpenAI is not configured or the deployment
      is unreachable.
    """
    if not ml_extraction_allowed(session=session):
        raise AIServiceUnavailableError(
            "Job readiness analysis is unavailable because machine learning consent has not been granted."
        )

    try:
        user_profile = build_user_profile(
            session=session,
            resume_id=request.resume_id,
            project_names=request.project_names,
            user_profile_input=request.user_profile,
        )
    except KeyError as exc:
        logger.exception("Missing project evidence during job readiness analysis")
        raise HTTPException(
            status_code=404,
            detail="Requested project evidence was not found.",
        ) from exc
    except LookupError as exc:
        logger.exception("Lookup error during job readiness analysis")
        raise HTTPException(
            status_code=404,
            detail="Requested resource was not found.",
        ) from exc
    except ValueError as exc:
        logger.exception("Invalid job readiness analysis request")
        raise HTTPException(
            status_code=400,
            detail="The request did not include enough valid evidence to analyze.",
        ) from exc

    result = run_job_readiness_analysis(
        job_description=request.job_description,
        user_profile=user_profile,
    )
    if result is None:
        raise AIServiceUnavailableError(
            "Job readiness analysis is unavailable. Confirm Azure OpenAI is enabled and "
            "the configured deployment targets GPT-4o mini."
        )
    return result
