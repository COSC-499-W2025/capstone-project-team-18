from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from src.core.ML.models.azure_openai_runtime import azure_chat_json, azure_openai_enabled
from src.core.ML.models.project_insight_constants import (
    DEFAULT_PROJECT_INSIGHT_REFILL_SCHEMA_NAME,
    PROJECT_INSIGHT_REFILL_SYSTEM_PROMPT,
    PROJECT_INSIGHT_REFILL_USER_PROMPT_TEMPLATE,
    project_insight_refill_response_schema,
)
from src.core.report.project.project_report import ProjectReport
from src.core.statistic.project_stat_collection import ProjectStatCollection
from src.core.statistic.statistic_models import WeightedSkills
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _normalize_message(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _dedupe_messages(messages: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for message in messages:
        cleaned = _normalize_message(message)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def _to_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, WeightedSkills):
        return {"skill_name": value.skill_name, "weight": value.weight}
    if isinstance(value, dict):
        return {str(_to_json_safe(key)): _to_json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]
    if hasattr(value, "skill_name") and hasattr(value, "weight"):
        return {
            "skill_name": str(getattr(value, "skill_name", "")),
            "weight": float(getattr(value, "weight", 0.0) or 0.0),
        }
    return str(value)


def _project_context(report: ProjectReport) -> dict[str, Any]:
    signal_keys = [
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value,
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value,
        ProjectStatCollection.IS_GROUP_PROJECT.value,
        ProjectStatCollection.TOTAL_AUTHORS.value,
        ProjectStatCollection.COLLABORATION_ROLE.value,
        ProjectStatCollection.ROLE_DESCRIPTION.value,
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
        ProjectStatCollection.PROJECT_FRAMEWORKS.value,
        ProjectStatCollection.PROJECT_THEMES.value,
        ProjectStatCollection.PROJECT_TAGS.value,
        ProjectStatCollection.PROJECT_TONE.value,
        ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value,
        ProjectStatCollection.WORK_PATTERN.value,
        ProjectStatCollection.PROJECT_START_DATE.value,
        ProjectStatCollection.PROJECT_END_DATE.value,
    ]

    signals: dict[str, Any] = {}
    for key in signal_keys:
        signals[str(key)] = _to_json_safe(report.get_value(key))

    file_paths = [getattr(file_report, "filepath", "") for file_report in report.file_reports[:20]]

    return {
        "project_name": report.project_name,
        "project_path": report.project_path,
        "file_paths": [path for path in file_paths if path],
        "signals": signals,
    }


def render_project_insight_refill_user_prompt(
    *,
    report: ProjectReport,
    style_examples: list[str],
    excluded_insights: list[str],
    count: int,
) -> str:
    return (
        PROJECT_INSIGHT_REFILL_USER_PROMPT_TEMPLATE
        .replace("{{count}}", str(max(1, int(count))))
        .replace("{{project_context}}", json.dumps(_project_context(report), indent=2, sort_keys=True))
        .replace("{{style_examples}}", json.dumps(_dedupe_messages(style_examples), indent=2))
        .replace("{{excluded_insights}}", json.dumps(_dedupe_messages(excluded_insights), indent=2))
    )


def _fallback_candidates(report: ProjectReport) -> list[str]:
    context = _project_context(report)
    project_name = str(context.get("project_name") or "this project")
    signals = context.get("signals", {})
    frameworks = signals.get(str(ProjectStatCollection.PROJECT_FRAMEWORKS.value)) or []
    skills = signals.get(str(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)) or []
    themes = signals.get(str(ProjectStatCollection.PROJECT_THEMES.value)) or []
    tags = signals.get(str(ProjectStatCollection.PROJECT_TAGS.value)) or []
    role = signals.get(str(ProjectStatCollection.COLLABORATION_ROLE.value))
    role_desc = signals.get(str(ProjectStatCollection.ROLE_DESCRIPTION.value))
    total_authors = signals.get(str(ProjectStatCollection.TOTAL_AUTHORS.value))
    work_pattern = signals.get(str(ProjectStatCollection.WORK_PATTERN.value))

    tech_terms = []
    for item in list(skills) + list(frameworks):
        if isinstance(item, dict) and item.get("skill_name"):
            tech_terms.append(str(item["skill_name"]))
        elif isinstance(item, str):
            tech_terms.append(item)
    tech_text = ", ".join(tech_terms[:3])
    theme_terms = [str(item) for item in list(themes) + list(tags) if str(item).strip()]
    theme_text = ", ".join(theme_terms[:3])

    candidates = [
        f"What concrete result or measurable improvement best shows the impact of your work on {project_name}?",
        f"If you wrote one resume bullet for {project_name}, which technical decision or deliverable would you highlight first?",
        f"Which part of {project_name} best demonstrates your ability to take work from idea to shipped outcome?",
        f"What challenge in {project_name} required the strongest problem-solving from you, and how did you resolve it?",
        f"Which piece of evidence from {project_name} most clearly proves your ownership and contribution?",
        f"What part of {project_name} best demonstrates engineering quality, reliability, or maintainability in resume-ready terms?",
        f"Which tradeoff or constraint in {project_name} would be strongest to explain in an interview or resume bullet?",
        f"What decision in {project_name} best shows how you prioritized scope, quality, and delivery?",
        f"Which part of {project_name} best demonstrates collaboration, alignment, or working effectively with others?",
        f"What part of {project_name} would you use to prove you can turn ambiguous work into a concrete shipped outcome?",
    ]

    if tech_text:
        candidates.append(
            f"You used {tech_text} in {project_name}. Where did those technologies make the biggest difference to the final outcome?"
        )
    if theme_text:
        candidates.append(
            f"The project signals for {project_name} point to themes like {theme_text}. Which of those best captures the value you delivered?"
        )
    if total_authors and int(total_authors) > 1:
        candidates.append(
            f"{project_name} involved {total_authors} contributors. What part of the collaboration are you most comfortable claiming ownership over?"
        )
    if role:
        candidates.append(
            f"Your inferred role on {project_name} was {role}. What deliverable or decision best proves that role in resume-ready terms?"
        )
    elif role_desc:
        candidates.append(
            f"Your contribution pattern on {project_name} suggests this role: {role_desc}. What concrete example demonstrates that contribution most clearly?"
        )
    if work_pattern:
        candidates.append(
            f"Your work pattern on {project_name} was {str(work_pattern).lower()}. What does that reveal about how you executed and delivered?"
        )

    return _dedupe_messages(candidates)


def _guaranteed_fallback_candidates(report: ProjectReport) -> list[str]:
    project_name = str(_project_context(report).get("project_name") or "this project")
    candidates: list[str] = []
    for angle in range(1, 51):
        candidates.extend(
            [
                f"Which outcome from {project_name} would make the strongest resume bullet about your direct impact?",
                f"What part of {project_name} best proves your ownership from scoping through delivery?",
                f"Which technical decision in {project_name} would you highlight to show engineering judgment?",
                f"What example from {project_name} best shows how you handled testing, quality, or reliability?",
                f"Which challenge from {project_name} best demonstrates your problem-solving and execution?",
                f"What collaboration example from {project_name} best shows how you worked with others to move the project forward?",
                f"What tradeoff from {project_name} best shows how you balanced speed, scope, and quality?",
                f"What evidence from {project_name} best shows your work produced a concrete shipped result?",
                f"From another angle, what contribution in {project_name} most clearly stands out as resume-worthy?",
                f"Looking at {project_name} from angle {angle}, what story best proves your value and contribution?",
            ]
        )
    return _dedupe_messages(candidates)


def _parse_azure_messages(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    insights = payload.get("insights")
    if not isinstance(insights, list):
        return []
    messages: list[str] = []
    for item in insights:
        if isinstance(item, dict) and isinstance(item.get("message"), str):
            messages.append(item["message"])
    return _dedupe_messages(messages)


def generate_project_insight_replacements(
    *,
    report: ProjectReport,
    existing_insights: list[str],
    dismissed_insights: list[str],
    count: int,
    allow_azure: bool = True,
) -> list[str]:
    needed = max(0, int(count))
    if needed == 0:
        return []

    excluded = _dedupe_messages(list(existing_insights) + list(dismissed_insights))
    style_examples = _dedupe_messages(existing_insights)[:3]
    generated: list[str] = []

    if allow_azure and azure_openai_enabled():
        user_prompt = render_project_insight_refill_user_prompt(
            report=report,
            style_examples=style_examples,
            excluded_insights=excluded,
            count=needed,
        )
        payload = azure_chat_json(
            system_prompt=PROJECT_INSIGHT_REFILL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=project_insight_refill_response_schema(needed),
            schema_name=DEFAULT_PROJECT_INSIGHT_REFILL_SCHEMA_NAME,
            max_tokens=240,
            temperature=0.4,
        )
        azure_messages = _parse_azure_messages(payload)
        for message in azure_messages:
            key = message.lower()
            if key in {item.lower() for item in excluded + generated}:
                continue
            generated.append(message)
            if len(generated) >= needed:
                return generated
        if azure_messages:
            logger.warning("Azure project insight refill produced insufficient unique insights for %s", report.project_name)

    for candidate_pool in (_fallback_candidates(report), _guaranteed_fallback_candidates(report)):
        for message in candidate_pool:
            key = message.lower()
            if key in {item.lower() for item in excluded + generated}:
                continue
            generated.append(message)
            if len(generated) >= needed:
                return generated

    return generated
