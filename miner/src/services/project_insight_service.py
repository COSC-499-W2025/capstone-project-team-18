from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from src.core.ML.models.azure_openai_runtime import azure_chat_json, azure_openai_enabled
from src.core.report.project.project_report import ProjectReport
from src.core.statistic.project_stat_collection import ProjectStatCollection
from src.core.statistic.statistic_models import WeightedSkills
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)
SCHEMA_NAME = "project_insight_refill"
SYSTEM_PROMPT = "\n".join([
    "You generate concise, evidence-based resume insight prompts for a technical project.",
    "Rules:", "Use only the supplied project context and signals.",
    "Do not assume a project type beyond the evidence provided.",
    "Do not invent tools, results, users, metrics, or responsibilities that are not supported by the context.",
    "Return exactly the requested number of new insight prompts when possible.",
    "Each insight must be distinct from the excluded insights and should not closely paraphrase them.",
    "Match the tone and structure of the style examples when examples are provided.",
    "Each insight should help a user turn project work into a stronger resume bullet or interview-ready accomplishment statement.",
    "Keep each insight concise, practical, and specific.",
    "Prefer reflective prompt/question wording over generic advice.",
    "Do not give vague career advice.",
    "Return valid JSON only that matches the required schema.",
])
USER_PROMPT_TEMPLATE = "\n".join([
    "Generate {{count}} new project insight prompt(s).", "", "Project context:", "{{project_context}}", "",
    "Style examples:", "{{style_examples}}", "", "Excluded insights:", "{{excluded_insights}}", "",
    "Output rules:", "- Return only new insight prompts that are grounded in the project context.",
    "- Avoid duplicates and close paraphrases of excluded insights.",
    "- Make each prompt resume-helpful, concrete, and tied to real project evidence.",
    "- Each prompt should be 1 to 2 sentences max.", "- Return JSON only.",
])
SIGNAL_KEYS = [
    ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value, ProjectStatCollection.USER_COMMIT_PERCENTAGE.value,
    ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value, ProjectStatCollection.IS_GROUP_PROJECT.value,
    ProjectStatCollection.TOTAL_AUTHORS.value, ProjectStatCollection.COLLABORATION_ROLE.value,
    ProjectStatCollection.ROLE_DESCRIPTION.value, ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
    ProjectStatCollection.PROJECT_FRAMEWORKS.value, ProjectStatCollection.PROJECT_THEMES.value,
    ProjectStatCollection.PROJECT_TAGS.value, ProjectStatCollection.PROJECT_TONE.value,
    ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value, ProjectStatCollection.WORK_PATTERN.value,
    ProjectStatCollection.PROJECT_START_DATE.value, ProjectStatCollection.PROJECT_END_DATE.value,
]
BASE_CANDIDATES = [
    "What concrete result or measurable improvement best shows the impact of your work on {project_name}?",
    "If you wrote one resume bullet for {project_name}, which technical decision or deliverable would you highlight first?",
    "Which part of {project_name} best demonstrates your ability to take work from idea to shipped outcome?",
    "What challenge in {project_name} required the strongest problem-solving from you, and how did you resolve it?",
    "Which piece of evidence from {project_name} most clearly proves your ownership and contribution?",
    "What part of {project_name} best demonstrates engineering quality, reliability, or maintainability in resume-ready terms?",
    "Which tradeoff or constraint in {project_name} would be strongest to explain in an interview or resume bullet?",
    "What decision in {project_name} best shows how you prioritized scope, quality, and delivery?",
    "Which part of {project_name} best demonstrates collaboration, alignment, or working effectively with others?",
    "What part of {project_name} would you use to prove you can turn ambiguous work into a concrete shipped outcome?",
]
GUARANTEED_CANDIDATES = [
    "Which outcome from {project_name} would make the strongest resume bullet about your direct impact?",
    "What part of {project_name} best proves your ownership from scoping through delivery?",
    "Which technical decision in {project_name} would you highlight to show engineering judgment?",
    "What example from {project_name} best shows how you handled testing, quality, or reliability?",
    "Which challenge from {project_name} best demonstrates your problem-solving and execution?",
    "What collaboration example from {project_name} best shows how you worked with others to move the project forward?",
    "What tradeoff from {project_name} best shows how you balanced speed, scope, and quality?",
    "What evidence from {project_name} best shows your work produced a concrete shipped result?",
    "From another angle, what contribution in {project_name} most clearly stands out as resume-worthy?",
    "Looking at {project_name} from angle {angle}, what story best proves your value and contribution?",
]


def _normalize_message(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _dedupe_messages(messages: list[str]) -> list[str]:
    seen: set[str] = set(); deduped: list[str] = []
    for message in messages:
        cleaned = _normalize_message(message)
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower()); deduped.append(cleaned)
    return deduped


def _to_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, Enum): return value.value
    if isinstance(value, WeightedSkills): return {"skill_name": value.skill_name, "weight": value.weight}
    if isinstance(value, dict): return {str(_to_json_safe(key)): _to_json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)): return [_to_json_safe(item) for item in value]
    if hasattr(value, "skill_name") and hasattr(value, "weight"):
        return {"skill_name": str(getattr(value, "skill_name", "")), "weight": float(getattr(value, "weight", 0.0) or 0.0)}
    return str(value)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool): return int(value)
    if isinstance(value, (int, float)): return int(value)
    if isinstance(value, str):
        try: return int(value.strip())
        except ValueError: return None
    return None


def _project_context(report: ProjectReport) -> dict[str, Any]:
    files = getattr(report, "file_reports", [])[:20]
    return {
        "project_name": _to_json_safe(getattr(report, "project_name", "")),
        "project_path": _to_json_safe(getattr(report, "project_path", "")),
        "file_paths": [_to_json_safe(getattr(file_report, "filepath", "")) for file_report in files if getattr(file_report, "filepath", "")],
        "signals": {str(key): _to_json_safe(report.get_value(key)) for key in SIGNAL_KEYS},
    }


def _response_schema(count: int) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "properties": {"insights": {"type": "array", "minItems": 1, "maxItems": max(1, int(count)), "items": {"type": "object", "additionalProperties": False, "properties": {"message": {"type": "string"}}, "required": ["message"]}}}, "required": ["insights"]}


def render_project_insight_refill_user_prompt(*, report: ProjectReport, style_examples: list[str], excluded_insights: list[str], count: int) -> str:
    return (USER_PROMPT_TEMPLATE.replace("{{count}}", str(max(1, int(count)))).replace("{{project_context}}", json.dumps(_project_context(report), indent=2, sort_keys=True)).replace("{{style_examples}}", json.dumps(_dedupe_messages(style_examples), indent=2)).replace("{{excluded_insights}}", json.dumps(_dedupe_messages(excluded_insights), indent=2)))


def _fallback_candidates(report: ProjectReport) -> list[str]:
    context = _project_context(report); project_name = str(context.get("project_name") or "this project"); signals = context["signals"]
    frameworks = signals.get(str(ProjectStatCollection.PROJECT_FRAMEWORKS.value)) or []
    skills = signals.get(str(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)) or []
    themes = signals.get(str(ProjectStatCollection.PROJECT_THEMES.value)) or []
    tags = signals.get(str(ProjectStatCollection.PROJECT_TAGS.value)) or []
    role = signals.get(str(ProjectStatCollection.COLLABORATION_ROLE.value)); role_desc = signals.get(str(ProjectStatCollection.ROLE_DESCRIPTION.value))
    total_authors = signals.get(str(ProjectStatCollection.TOTAL_AUTHORS.value)); work_pattern = signals.get(str(ProjectStatCollection.WORK_PATTERN.value))
    tech_text = ", ".join(str(item["skill_name"]) if isinstance(item, dict) and item.get("skill_name") else str(item) for item in [*skills, *frameworks] if (isinstance(item, dict) and item.get("skill_name")) or isinstance(item, str))
    theme_text = ", ".join(str(item) for item in [*themes, *tags] if str(item).strip())
    extras = [
        *([f"You used {', '.join(tech_text.split(', ')[:3])} in {project_name}. Where did those technologies make the biggest difference to the final outcome?"] if tech_text else []),
        *([f"The project signals for {project_name} point to themes like {', '.join(theme_text.split(', ')[:3])}. Which of those best captures the value you delivered?"] if theme_text else []),
        *([f"{project_name} involved {total_authors} contributors. What part of the collaboration are you most comfortable claiming ownership over?"] if (_as_int(total_authors) or 0) > 1 else []),
        *([f"Your inferred role on {project_name} was {role}. What deliverable or decision best proves that role in resume-ready terms?"] if role else []),
        *([f"Your contribution pattern on {project_name} suggests this role: {role_desc}. What concrete example demonstrates that contribution most clearly?"] if role_desc and not role else []),
        *([f"Your work pattern on {project_name} was {str(work_pattern).lower()}. What does that reveal about how you executed and delivered?"] if work_pattern else []),
    ]
    return _dedupe_messages([template.format(project_name=project_name) for template in BASE_CANDIDATES] + extras)


def _guaranteed_fallback_candidates(report: ProjectReport, needed: int) -> list[str]:
    project_name = str(_project_context(report).get("project_name") or "this project")
    rounds = max(1, (needed + len(GUARANTEED_CANDIDATES) - 1) // len(GUARANTEED_CANDIDATES) + 1)
    return _dedupe_messages([template.format(project_name=project_name, angle=angle) for angle in range(1, rounds + 1) for template in GUARANTEED_CANDIDATES])


def _parse_azure_messages(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("insights"), list): return []
    return _dedupe_messages([item["message"] for item in payload["insights"] if isinstance(item, dict) and isinstance(item.get("message"), str)])


def _append_unique(target: list[str], candidates: list[str], excluded: set[str], needed: int) -> bool:
    for message in candidates:
        key = message.lower()
        if key not in excluded:
            excluded.add(key); target.append(message)
            if len(target) >= needed: return True
    return False


def generate_project_insight_replacements(report: ProjectReport, existing_insights: list[str], dismissed_insights: list[str], count: int, allow_azure: bool = True) -> list[str]:
    needed = max(0, int(count))
    if needed == 0: return []
    excluded_messages = _dedupe_messages([*existing_insights, *dismissed_insights]); excluded = {message.lower() for message in excluded_messages}; generated: list[str] = []
    if allow_azure and azure_openai_enabled():
        payload = azure_chat_json(system_prompt=SYSTEM_PROMPT, user_prompt=render_project_insight_refill_user_prompt(report=report, style_examples=_dedupe_messages(existing_insights)[:3], excluded_insights=excluded_messages, count=needed), response_schema=_response_schema(needed), schema_name=SCHEMA_NAME, max_tokens=240, temperature=0.4)
        azure_messages = _parse_azure_messages(payload)
        if _append_unique(generated, azure_messages, excluded, needed): return generated
        if azure_messages: logger.warning("Azure project insight refill produced insufficient unique insights for %s", report.project_name)
    _append_unique(generated, _fallback_candidates(report), excluded, needed)
    if len(generated) < needed: _append_unique(generated, _guaranteed_fallback_candidates(report, needed + len(excluded)), excluded, needed)
    return generated
