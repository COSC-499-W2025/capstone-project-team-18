from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Session

from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.services.interview_service import (
    InterviewAnswerResult,
    InterviewStartResult,
    build_interview_context,
    generate_followup,
    generate_question,
)
from src.services.job_readiness_service import JobReadinessUserProfileInput

router = APIRouter(
    prefix="/interview",
    tags=["interview"],
)
logger = get_logger(__name__)


class InterviewBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_description: str = Field(min_length=1)
    resume_id: int | None = None
    project_names: list[str] = Field(default_factory=list)
    user_profile: JobReadinessUserProfileInput | None = None
    difficulty: str = "intermediate"

    @field_validator("job_description")
    @classmethod
    def validate_job_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("job_description must contain non-whitespace characters")
        return stripped

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        stripped = value.strip().lower()
        if stripped not in {"beginner", "intermediate", "advanced"}:
            raise ValueError("difficulty must be beginner, intermediate, or advanced")
        return stripped


class InterviewStartRequest(InterviewBaseRequest):
    pass


class InterviewAnswerRequest(InterviewBaseRequest):
    current_question: str = Field(min_length=1)
    user_answer: str = Field(min_length=1)

    @field_validator("current_question", "user_answer")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must contain non-whitespace characters")
        return stripped


def _build_context_or_raise(
    *,
    session: Session,
    job_description: str,
    resume_id: int | None,
    project_names: list[str],
    user_profile: JobReadinessUserProfileInput | None,
):
    try:
        return build_interview_context(
            session=session,
            job_description=job_description,
            resume_id=resume_id,
            project_names=project_names,
            user_profile_input=user_profile,
        )
    except KeyError as exc:
        logger.exception("Missing project evidence during interview analysis")
        raise HTTPException(
            status_code=404,
            detail="Requested project evidence was not found.",
        ) from exc
    except LookupError as exc:
        logger.exception("Lookup error during interview analysis")
        raise HTTPException(
            status_code=404,
            detail="Requested resource was not found.",
        ) from exc
    except ValueError as exc:
        logger.exception("Invalid interview analysis request")
        raise HTTPException(
            status_code=400,
            detail="The request did not include enough valid evidence to analyze.",
        ) from exc


@router.post("/start", response_model=InterviewStartResult)
def start_interview(
    request: InterviewStartRequest,
    session: Session = Depends(get_session),
):
    interview_context = _build_context_or_raise(
        session=session,
        job_description=request.job_description,
        resume_id=request.resume_id,
        project_names=request.project_names,
        user_profile=request.user_profile,
    )
    result = generate_question(
        job_description=request.job_description,
        interview_context=interview_context,
        difficulty=request.difficulty,
    )
    if result is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Mock interview generation is unavailable. Confirm Azure OpenAI is enabled and "
                "the configured deployment targets GPT-4o mini."
            ),
        )
    return result


@router.post("/answer", response_model=InterviewAnswerResult)
def answer_interview_question(
    request: InterviewAnswerRequest,
    session: Session = Depends(get_session),
):
    interview_context = _build_context_or_raise(
        session=session,
        job_description=request.job_description,
        resume_id=request.resume_id,
        project_names=request.project_names,
        user_profile=request.user_profile,
    )
    result = generate_followup(
        user_answer=request.user_answer,
        current_question=request.current_question,
        job_description=request.job_description,
        interview_context=interview_context,
        difficulty=request.difficulty,
    )
    if result is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Mock interview generation is unavailable. Confirm Azure OpenAI is enabled and "
                "the configured deployment targets GPT-4o mini."
            ),
        )
    return result
