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
    generate_question,
    evaluate_answer,
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

    @field_validator("job_description")
    @classmethod
    def validate_job_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("job_description must contain non-whitespace characters")
        return stripped


class InterviewStartRequest(InterviewBaseRequest):
    pass


class InterviewAnswerRequest(InterviewBaseRequest):
    current_question: str = Field(min_length=1)
    user_answer: str = Field(min_length=1)
    current_project_name: str | None = Field(
        default=None,
        description=(
            "Optional project tied to the current question so follow-up evaluation stays "
            "anchored to the same project evidence."
        ),
    )
    current_fit_dimension: str | None = Field(
        default=None,
        description=(
            "Optional job-fit dimension for the current question. When provided, answer "
            "evaluation continues on that same dimension until coverage is complete."
        ),
    )
    covered_dimensions: list[str] = Field(default_factory=list)
    retry_same_question: bool = False

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
    """Start a mock interview and return the first generated question.

    This endpoint initializes interview context from the supplied job description and
    optional candidate evidence, then generates the first interview question for the
    client to present to the user.

    Request parameters:
    - `job_description`: Required target role description used to tailor the interview.
    - `resume_id`: Optional resume record to include in the interview context.
    - `project_names`: Optional list of project names to bias question generation toward.
    - `user_profile`: Optional structured user profile data used when resume/project
      evidence is incomplete.

    Typical usage:
    1. Call `/interview/start` with the job description and any available evidence.
    2. Present the returned question to the user.
    3. Send the user's answer, along with the returned context fields, to
       `/interview/answer` for feedback and the next question.
    """
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
    """Evaluate an interview answer and return feedback plus the next question.

    This endpoint scores the user's response to the current interview question,
    generates coaching feedback, and decides whether to retry the same topic or
    advance to the next question.

    Request parameters:
    - `job_description`: Required target role description used to evaluate relevance.
    - `resume_id`: Optional resume record to include in the interview context.
    - `project_names`: Optional list of project names used to ground question flow.
    - `user_profile`: Optional structured user profile data used when resume/project
      evidence is incomplete.
    - `current_question`: Required question the user is answering.
    - `user_answer`: Required free-text response from the user.
    - `current_project_name`: Optional project currently being discussed so follow-up
      questions remain anchored to the same project.
    - `current_fit_dimension`: Optional fit dimension currently being discussed so the
      interview can continue on the same topic until it is sufficiently covered.
    - `covered_dimensions`: Optional history of dimensions already covered in the
      interview flow.
    - `retry_same_question`: Optional flag indicating the client is retrying the
      current question after prior feedback.

    Typical usage:
    1. Call `/interview/start` to receive the first question.
    2. After each user response, call `/interview/answer` with the current question,
       answer, and any returned state fields.
    3. Use the response feedback and next question to continue the mock interview.
    """
    interview_context = _build_context_or_raise(
        session=session,
        job_description=request.job_description,
        resume_id=request.resume_id,
        project_names=request.project_names,
        user_profile=request.user_profile,
    )
    result = evaluate_answer(
        user_answer=request.user_answer,
        current_question=request.current_question,
        job_description=request.job_description,
        interview_context=interview_context,
        current_project_name=request.current_project_name,
        current_fit_dimension=request.current_fit_dimension,
        covered_dimensions=request.covered_dimensions,
        retry_same_question=request.retry_same_question,
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
