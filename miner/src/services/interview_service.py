from __future__ import annotations

import json
import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlmodel import Session

from src.core.ML.models.azure_openai_runtime import azure_chat_json, azure_openai_enabled
from src.core.ML.models.interview_constants import (
    DEFAULT_INTERVIEW_ANSWER_SCHEMA_NAME,
    DEFAULT_INTERVIEW_START_SCHEMA_NAME,
    INTERVIEW_ANSWER_RESPONSE_SCHEMA,
    INTERVIEW_ANSWER_SYSTEM_PROMPT,
    INTERVIEW_ANSWER_USER_PROMPT_TEMPLATE,
    INTERVIEW_START_RESPONSE_SCHEMA,
    INTERVIEW_START_SYSTEM_PROMPT,
    INTERVIEW_START_USER_PROMPT_TEMPLATE,
)
from src.infrastructure.log.logging import get_logger
from src.services.job_readiness_service import (
    JobReadinessUserProfileInput,
    build_user_profile,
    run_job_readiness_analysis,
)


InterviewDifficulty = Literal["beginner", "intermediate", "advanced"]
InterviewQuestionCategory = Literal["project_based", "role_specific", "skill_gap"]

logger = get_logger(__name__)


class InterviewStartResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    question_category: InterviewQuestionCategory
    interviewer_focus: str = Field(min_length=1)


class InterviewFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strengths: str = Field(min_length=1)
    improvements: str = Field(min_length=1)
    example_answer: str = Field(min_length=1)


class InterviewAnswerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_acceptable: bool
    feedback: InterviewFeedback
    next_question: str = Field(min_length=1)
    next_question_category: InterviewQuestionCategory


def _deployment_name() -> str | None:
    return (os.environ.get("AZURE_OPENAI_INTERVIEW_DEPLOYMENT") or "").strip() or None


def _normalize_difficulty(value: str | None) -> InterviewDifficulty:
    lowered = (value or "intermediate").strip().lower()
    if lowered in {"beginner", "intermediate", "advanced"}:
        return lowered  # type: ignore[return-value]
    return "intermediate"


def _readiness_signals(
    *,
    job_description: str,
    user_profile: dict[str, Any],
) -> dict[str, Any]:
    result = run_job_readiness_analysis(
        job_description=job_description,
        user_profile=user_profile,
    )
    if result is None:
        return {"strengths": [], "weaknesses": [], "suggestions": []}

    return {
        "strengths": [item.model_dump() for item in result.strengths],
        "weaknesses": [item.model_dump() for item in result.weaknesses],
        "suggestions": [item.model_dump() for item in result.suggestions],
    }


def build_interview_context(
    *,
    session: Session,
    job_description: str,
    resume_id: int | None = None,
    project_names: list[str] | None = None,
    user_profile_input: JobReadinessUserProfileInput | None = None,
) -> dict[str, Any]:
    user_profile = build_user_profile(
        session=session,
        resume_id=resume_id,
        project_names=project_names,
        user_profile_input=user_profile_input,
    )

    return {
        "user_profile": user_profile,
        "job_readiness_signals": _readiness_signals(
            job_description=job_description,
            user_profile=user_profile,
        ),
    }


def render_interview_start_prompt(
    *,
    job_description: str,
    interview_context: dict[str, Any],
    difficulty: InterviewDifficulty,
) -> str:
    return (
        INTERVIEW_START_USER_PROMPT_TEMPLATE
        .replace("{{difficulty}}", difficulty)
        .replace("{{job_description}}", job_description)
        .replace("{{interview_context}}", json.dumps(interview_context, indent=2, sort_keys=True))
    )


def render_interview_answer_prompt(
    *,
    job_description: str,
    interview_context: dict[str, Any],
    current_question: str,
    user_answer: str,
    difficulty: InterviewDifficulty,
) -> str:
    return (
        INTERVIEW_ANSWER_USER_PROMPT_TEMPLATE
        .replace("{{difficulty}}", difficulty)
        .replace("{{job_description}}", job_description)
        .replace("{{interview_context}}", json.dumps(interview_context, indent=2, sort_keys=True))
        .replace("{{current_question}}", current_question)
        .replace("{{user_answer}}", user_answer)
    )


def _parse_start_payload(payload: dict[str, Any] | None) -> InterviewStartResult | None:
    if payload is None:
        logger.warning("[TASK=INTERVIEW_START] Azure returned no payload")
        return None
    try:
        return InterviewStartResult.model_validate(payload)
    except ValidationError as exc:
        logger.warning(
            "[TASK=INTERVIEW_START] Payload failed validation: %s | payload=%s",
            exc,
            json.dumps(payload, ensure_ascii=True)[:1200],
        )
        return None


def _parse_answer_payload(payload: dict[str, Any] | None) -> InterviewAnswerResult | None:
    if payload is None:
        logger.warning("[TASK=INTERVIEW_ANSWER] Azure returned no payload")
        return None
    if isinstance(payload, dict):
        feedback = payload.get("feedback")
        if isinstance(feedback, dict):
            if not str(feedback.get("strengths", "")).strip():
                feedback["strengths"] = (
                    "You responded to the prompt, but the answer did not provide enough technical detail to assess."
                )
            if not str(feedback.get("improvements", "")).strip():
                feedback["improvements"] = (
                    "The answer needs more specificity about the technical approach, implementation details, and tradeoffs."
                )
            if not str(feedback.get("example_answer", "")).strip():
                feedback["example_answer"] = (
                    "A stronger answer would describe the project context, the main technical decisions, one challenge, and how reliability, testing, or performance were handled."
                )
    try:
        return InterviewAnswerResult.model_validate(payload)
    except ValidationError as exc:
        logger.warning(
            "[TASK=INTERVIEW_ANSWER] Payload failed validation: %s | payload=%s",
            exc,
            json.dumps(payload, ensure_ascii=True)[:1600],
        )
        return None




def generate_question(
    *,
    job_description: str,
    interview_context: dict[str, Any],
    difficulty: str = "intermediate",
    max_attempts: int = 2,
) -> InterviewStartResult | None:
    if not azure_openai_enabled():
        logger.info("[TASK=INTERVIEW_START] Skipping generation because Azure OpenAI is disabled")
        return None

    user_prompt = render_interview_start_prompt(
        job_description=job_description,
        interview_context=interview_context,
        difficulty=_normalize_difficulty(difficulty),
    )
    for attempt in range(max_attempts):
        payload = azure_chat_json(
            system_prompt=INTERVIEW_START_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=INTERVIEW_START_RESPONSE_SCHEMA,
            schema_name=DEFAULT_INTERVIEW_START_SCHEMA_NAME,
            max_tokens=320,
            temperature=0.2,
            deployment=_deployment_name(),
        )
        result = _parse_start_payload(payload)
        if result is not None:
            logger.info(
                "[TASK=INTERVIEW_START] Generated question successfully on attempt %d (category=%s)",
                attempt + 1,
                result.question_category,
            )
            return result
        logger.warning(
            "[TASK=INTERVIEW_START] Attempt %d returned no valid structured question",
            attempt + 1,
        )
    return None


def evaluate_answer(
    *,
    user_answer: str,
    current_question: str,
    job_description: str,
    interview_context: dict[str, Any],
    difficulty: str = "intermediate",
    max_attempts: int = 2,
) -> InterviewAnswerResult | None:
    if not azure_openai_enabled():
        logger.info("[TASK=INTERVIEW_ANSWER] Skipping evaluation because Azure OpenAI is disabled")
        return None

    user_prompt = render_interview_answer_prompt(
        job_description=job_description,
        interview_context=interview_context,
        current_question=current_question,
        user_answer=user_answer,
        difficulty=_normalize_difficulty(difficulty),
    )
    for attempt in range(max_attempts):
        payload = azure_chat_json(
            system_prompt=INTERVIEW_ANSWER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=INTERVIEW_ANSWER_RESPONSE_SCHEMA,
            schema_name=DEFAULT_INTERVIEW_ANSWER_SCHEMA_NAME,
            max_tokens=700,
            temperature=0.2,
            deployment=_deployment_name(),
        )
        result = _parse_answer_payload(payload)
        if result is not None:
            logger.info(
                "[TASK=INTERVIEW_ANSWER] Evaluated answer successfully on attempt %d (next_category=%s)",
                attempt + 1,
                result.next_question_category,
            )
            return result
        logger.warning(
            "[TASK=INTERVIEW_ANSWER] Attempt %d returned no valid structured evaluation",
            attempt + 1,
        )
    return None


def generate_followup(
    *,
    user_answer: str,
    current_question: str,
    job_description: str,
    interview_context: dict[str, Any],
    difficulty: str = "intermediate",
    max_attempts: int = 2,
) -> InterviewAnswerResult | None:
    return evaluate_answer(
        user_answer=user_answer,
        current_question=current_question,
        job_description=job_description,
        interview_context=interview_context,
        difficulty=difficulty,
        max_attempts=max_attempts,
    )
