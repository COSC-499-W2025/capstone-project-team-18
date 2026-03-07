from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

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


class JobReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_description: str = Field(min_length=1)
    resume_id: int | None = None
    project_names: list[str] = Field(default_factory=list)
    user_profile: JobReadinessUserProfileInput | None = None


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
        raise HTTPException(status_code=404, detail=f"Missing project evidence: {exc.args[0]}") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = run_job_readiness_analysis(
        job_description=request.job_description.strip(),
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
