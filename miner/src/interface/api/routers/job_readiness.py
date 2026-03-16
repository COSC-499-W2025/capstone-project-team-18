from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Session

from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.services.job_readiness_service import (
    JobReadinessResult,
    JobReadinessUserProfileInput,
    build_user_profile,
    run_job_readiness_analysis,
)

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
        raise HTTPException(
            status_code=503,
            detail=(
                "Job readiness analysis is unavailable. Confirm Azure OpenAI is enabled and "
                "the configured deployment targets GPT-4o mini."
            ),
        )
    return result
