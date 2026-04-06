from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlmodel import Session

from src.core.ML.models.azure_openai_runtime import azure_chat_json, azure_openai_enabled
from src.core.ML.models.job_readiness_constants import (
    DEFAULT_JOB_READINESS_SCHEMA_NAME,
    JOB_READINESS_RESPONSE_SCHEMA,
    JOB_READINESS_SYSTEM_PROMPT,
    JOB_READINESS_USER_PROMPT_TEMPLATE,
)
from src.database.api.CRUD.projects import get_project_report_models_by_names
from src.database.api.CRUD.resume import get_resume_model_by_id
from src.database.api.models import ProjectReportModel, ResumeModel
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


class RankedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str
    reason: str
    rank: int = Field(ge=1)


class PrioritizedSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str
    reason: str
    priority: int = Field(ge=1)
    action_type: str
    resource_name: str
    resource_type: str
    resource_hint: str


class JobReadinessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[RankedFinding]
    weaknesses: list[RankedFinding]
    suggestions: list[PrioritizedSuggestion]


class JobReadinessUserProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_text: str | None = None
    project_summaries: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    extracted_skills: list[str] = Field(default_factory=list)
    repository_history_summary: list[str] = Field(default_factory=list)
    repository_file_evidence: list[dict[str, Any]] = Field(default_factory=list)
    collaboration_signals: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class JobReadinessAnalysisOutcome:
    result: JobReadinessResult | None
    error_message: str | None = None


def render_job_readiness_user_prompt(job_description: str, user_profile: dict[str, Any]) -> str:
    return (
        JOB_READINESS_USER_PROMPT_TEMPLATE
        .replace("{{job_description}}", job_description)
        .replace("{{user_profile}}", json.dumps(user_profile, indent=2, sort_keys=True))
    )


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.startswith("__enum__:"):
        parts = text.split(":")
        if parts:
            return parts[-1].strip()
    return text

def _suggestion_is_actionable(suggestion: PrioritizedSuggestion) -> bool:
    action_verbs = {
        "build", "create", "deploy", "add", "complete", "document", "implement",
        "publish", "describe", "containerize", "write", "ship", "refactor",
    }
    weak_verbs = ("learn", "enhance", "familiarize", "explore", "improve skills")
    artifact_terms = (
        "project", "demo", "portfolio", "resume", "bullet", "artifact", "case study",
        "feature", "deployment", "app", "service", "tutorial", "documentation",
        "guide", "guided learning path", "certificate",
    )

    item_text = suggestion.item.strip().lower()
    first_word = item_text.split(maxsplit=1)[0] if item_text else ""
    combined = " ".join(
        [
            suggestion.item,
            suggestion.reason,
            suggestion.action_type,
            suggestion.resource_name,
            suggestion.resource_type,
            suggestion.resource_hint,
        ]
    ).lower()

    if first_word not in action_verbs:
        return False

    if any(phrase in item_text for phrase in weak_verbs):
        return any(term in combined for term in artifact_terms)

    return any(term in combined for term in artifact_terms)


def _suggestions_are_actionable(result: JobReadinessResult) -> bool:
    return all(_suggestion_is_actionable(suggestion) for suggestion in result.suggestions)


def _resume_to_text(resume: ResumeModel) -> str:
    lines: list[str] = []
    if resume.email:
        lines.append(f"Email: {resume.email}")
    if resume.github:
        lines.append(f"GitHub: {resume.github}")
    if resume.skills:
        lines.append(f"Skills: {', '.join(_clean_value(skill) for skill in resume.skills)}")
    for item in resume.items:
        lines.append(f"Role: {item.title}")
        if item.frameworks:
            lines.append(f"Frameworks: {', '.join(_clean_value(framework) for framework in item.frameworks)}")
        for bullet in item.bullet_points:
            lines.append(f"- {bullet}")
    return "\n".join(lines)


def _project_summary(project: ProjectReportModel) -> str:
    summary_lines = [f"Project: {project.project_name}"]
    if project.showcase_title:
        summary_lines.append(f"Showcase title: {project.showcase_title}")
    if project.showcase_frameworks:
        summary_lines.append(f"Frameworks: {', '.join(_clean_value(framework) for framework in project.showcase_frameworks)}")
    if project.showcase_bullet_points:
        summary_lines.extend(f"- {bullet}" for bullet in project.showcase_bullet_points)
    stat_summary = _project_stat_summary_lines(project.statistic)
    if stat_summary:
        summary_lines.extend(stat_summary)
    file_summary = _project_file_signal_summary(project)
    if file_summary:
        summary_lines.extend(file_summary)
    return "\n".join(summary_lines)


def _project_history_summary(project: ProjectReportModel) -> str:
    return json.dumps(
        {
            "project_name": project.project_name,
            "created_at": project.created_at.isoformat(),
            "last_updated": project.last_updated.isoformat(),
            "analyzed_count": project.analyzed_count,
            "statistics": project.statistic,
        },
        sort_keys=True,
        default=str,
    )


def _project_file_evidence(project: ProjectReportModel) -> dict[str, Any]:
    return {
        "project_name": project.project_name,
        "files": [file_report.file_path for file_report in project.file_reports],
    }


def _weighted_skill_names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    extracted: list[str] = []
    for item in values:
        if isinstance(item, dict) and item.get("skill_name"):
            extracted.append(_clean_value(item["skill_name"]))
        elif hasattr(item, "skill_name"):
            extracted.append(_clean_value(item.skill_name))
    return extracted


def _top_mapping_keys(values: Any, limit: int = 5) -> list[str]:
    if not isinstance(values, dict):
        return []
    ordered = sorted(
        values.items(),
        key=lambda pair: pair[1] if isinstance(pair[1], (int, float)) else 0,
        reverse=True,
    )
    return [_clean_value(key) for key, _ in ordered[:limit]]


def _project_stat_summary_lines(statistic: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    frameworks = _weighted_skill_names(statistic.get("PROJECT_FRAMEWORKS"))
    if frameworks:
        lines.append(f"Detected frameworks/packages: {', '.join(frameworks[:8])}")

    skills = _weighted_skill_names(statistic.get("PROJECT_SKILLS_DEMONSTRATED"))
    if skills:
        lines.append(f"Demonstrated skills: {', '.join(skills[:8])}")

    coding_languages = _top_mapping_keys(statistic.get("CODING_LANGUAGE_RATIO"))
    if coding_languages:
        lines.append(f"Primary languages: {', '.join(coding_languages[:5])}")

    tags = statistic.get("PROJECT_TAGS")
    if isinstance(tags, list) and tags:
        lines.append(f"README tags: {', '.join(_clean_value(tag) for tag in tags[:8])}")

    themes = statistic.get("PROJECT_THEMES")
    if isinstance(themes, list) and themes:
        lines.append(f"README themes: {', '.join(_clean_value(theme) for theme in themes[:8])}")

    collaboration_role = statistic.get("COLLABORATION_ROLE")
    if collaboration_role:
        lines.append(f"Collaboration role: {_clean_value(collaboration_role)}")

    role_description = statistic.get("ROLE_DESCRIPTION")
    if role_description:
        lines.append(f"Role description: {_clean_value(role_description)}")

    work_pattern = statistic.get("WORK_PATTERN")
    if work_pattern:
        lines.append(f"Work pattern: {_clean_value(work_pattern)}")

    commit_types = _top_mapping_keys(statistic.get("COMMIT_TYPE_DISTRIBUTION"))
    if commit_types:
        lines.append(f"Commit patterns: {', '.join(commit_types[:5])}")

    total_authors = statistic.get("TOTAL_AUTHORS")
    if isinstance(total_authors, int) and total_authors > 0:
        lines.append(f"Total authors: {total_authors}")

    is_group_project = statistic.get("IS_GROUP_PROJECT")
    if isinstance(is_group_project, bool):
        lines.append(f"Group project: {'yes' if is_group_project else 'no'}")

    commit_percentage = statistic.get("USER_COMMIT_PERCENTAGE")
    if isinstance(commit_percentage, (int, float)):
        lines.append(f"User commit percentage: {round(float(commit_percentage) * 100, 1)}%")

    contribution_percentage = statistic.get("TOTAL_CONTRIBUTION_PERCENTAGE")
    if isinstance(contribution_percentage, (int, float)):
        lines.append(f"User line contribution percentage: {round(float(contribution_percentage) * 100, 1)}%")

    return lines


def _project_file_signal_summary(project: ProjectReportModel) -> list[str]:
    file_paths = [file_report.file_path for file_report in project.file_reports]
    if not file_paths:
        return []

    lowered = [path.lower() for path in file_paths]
    evidence_lines = [f"Representative files: {', '.join(file_paths[:8])}"]

    api_files = [path for path in file_paths if any(token in path.lower() for token in ("api", "route", "endpoint", "controller"))]
    sql_files = [path for path in file_paths if path.lower().endswith(".sql")]
    test_files = [path for path in file_paths if any(token in path.lower() for token in ("test", "spec"))]
    docker_files = [path for path in file_paths if "docker" in path.lower()]
    ci_files = [path for path in file_paths if any(token in path.lower() for token in (".github/workflows", "gitlab-ci", "jenkins", "pipeline"))]
    frontend_files = [path for path in file_paths if any(path.lower().endswith(ext) for ext in (".tsx", ".jsx", ".html", ".css", ".scss"))]

    if api_files:
        evidence_lines.append(f"API/backend file signals: {', '.join(api_files[:5])}")
    if sql_files:
        evidence_lines.append(f"SQL/database file signals: {', '.join(sql_files[:5])}")
    if test_files:
        evidence_lines.append(f"Testing file signals: {', '.join(test_files[:5])}")
    if docker_files:
        evidence_lines.append(f"Docker/deployment file signals: {', '.join(docker_files[:5])}")
    if ci_files:
        evidence_lines.append(f"CI/CD file signals: {', '.join(ci_files[:5])}")
    if frontend_files:
        evidence_lines.append(f"Frontend collaboration file signals: {', '.join(frontend_files[:5])}")

    return evidence_lines


def _project_tags_from_stats(project: ProjectReportModel) -> list[str]:
    statistic = project.statistic
    tags: list[str] = []

    for key in ("PROJECT_TAGS", "PROJECT_THEMES"):
        values = statistic.get(key)
        if isinstance(values, list):
            tags.extend(_clean_value(value) for value in values)

    for key in ("COLLABORATION_ROLE", "WORK_PATTERN", "ROLE_DESCRIPTION", "PROJECT_TONE"):
        value = statistic.get(key)
        if value:
            tags.append(_clean_value(value))

    total_authors = statistic.get("TOTAL_AUTHORS")
    if isinstance(total_authors, int) and total_authors > 1:
        tags.append("team collaboration")

    is_group_project = statistic.get("IS_GROUP_PROJECT")
    if is_group_project is True:
        tags.append("group project")

    return tags


def _project_skills_from_stats(project: ProjectReportModel) -> list[str]:
    statistic = project.statistic
    skills: list[str] = []
    skills.extend(_weighted_skill_names(statistic.get("PROJECT_FRAMEWORKS")))
    skills.extend(_weighted_skill_names(statistic.get("PROJECT_SKILLS_DEMONSTRATED")))
    skills.extend(_top_mapping_keys(statistic.get("CODING_LANGUAGE_RATIO")))

    file_paths = [file_report.file_path for file_report in project.file_reports]
    lowered = [path.lower() for path in file_paths]
    if any(path.endswith(".sql") for path in lowered):
        skills.append("SQL")
    if any(token in path for path in lowered for token in ("api", "route", "endpoint", "controller")):
        skills.append("API development")
    if any(token in path for path in lowered for token in ("test", "spec")):
        skills.append("Testing")
    if any("docker" in path for path in lowered):
        skills.append("Docker")
    if any(token in path for path in lowered for token in (".github/workflows", "gitlab-ci", "jenkins", "pipeline")):
        skills.append("CI/CD")
    if any(path.endswith(ext) for path in lowered for ext in (".tsx", ".jsx", ".html", ".css", ".scss")):
        skills.append("Frontend collaboration")

    total_authors = statistic.get("TOTAL_AUTHORS")
    if isinstance(total_authors, int) and total_authors > 1:
        skills.append("Git collaboration")
    if isinstance(statistic.get("USER_COMMIT_PERCENTAGE"), (int, float)):
        skills.append("Git workflows")

    return skills


def _derive_collaboration_signals(
    *,
    project_summaries: list[str],
    tags: list[str],
    repository_history_summary: list[str],
    repository_file_evidence: list[dict[str, Any]],
) -> list[str]:
    signals: list[str] = []

    collaboration_terms = (
        "team",
        "collaborat",
        "cross-functional",
        "communication",
        "stakeholder",
        "review",
        "handoff",
        "shared ownership",
    )

    searchable_text = "\n".join(project_summaries + tags + repository_history_summary).lower()
    if any(term in searchable_text for term in collaboration_terms):
        signals.append("Existing project evidence references teamwork, collaboration, or cross-functional delivery.")

    for evidence in repository_file_evidence:
        files = [str(path).lower() for path in evidence.get("files", [])]
        if not files:
            continue

        has_backend = any(token in path for path in files for token in ("api", "route", "endpoint", "controller"))
        has_frontend = any(path.endswith(ext) for path in files for ext in (".tsx", ".jsx", ".html", ".css", ".scss"))
        has_tests = any(token in path for path in files for token in ("test", "spec"))
        has_delivery = any(token in path for path in files for token in ("docker", ".github/workflows", "gitlab-ci", "jenkins", "pipeline"))

        covered_areas = sum([has_backend, has_frontend, has_tests, has_delivery])
        if covered_areas >= 3:
            signals.append(
                "Repository evidence spans multiple delivery areas such as backend, frontend, testing, or CI/CD."
            )
            break

    return _dedupe_strings(signals)


def build_user_profile(
    *,
    session: Session,
    resume_id: int | None = None,
    project_names: list[str] | None = None,
    user_profile_input: JobReadinessUserProfileInput | None = None,
) -> dict[str, Any]:
    project_names = list(project_names or [])
    provided = user_profile_input or JobReadinessUserProfileInput()

    resume = get_resume_model_by_id(session, resume_id) if resume_id is not None else None
    if resume_id is not None and resume is None:
        raise LookupError(f"No resume found with id {resume_id}")
    if resume is not None and not project_names:
        project_names = [item.project_name for item in resume.items if item.project_name]

    projects = get_project_report_models_by_names(session, project_names)

    project_summaries = list(provided.project_summaries)
    tags = list(provided.tags)
    extracted_skills = list(provided.extracted_skills)
    history_summaries = list(provided.repository_history_summary)
    file_evidence = list(provided.repository_file_evidence)
    collaboration_signals = list(provided.collaboration_signals)

    if resume is not None:
        extracted_skills.extend(_clean_value(skill) for skill in resume.skills)
        for item in resume.items:
            extracted_skills.extend(_clean_value(framework) for framework in item.frameworks)
            tags.append(_clean_value(item.title))

    for project in projects:
        project_summaries.append(_project_summary(project))
        tags.extend(_clean_value(framework) for framework in project.showcase_frameworks)
        tags.extend(_project_tags_from_stats(project))
        extracted_skills.extend(_clean_value(framework) for framework in project.showcase_frameworks)
        extracted_skills.extend(_project_skills_from_stats(project))
        history_summaries.append(_project_history_summary(project))
        file_evidence.append(_project_file_evidence(project))

    user_profile = {
        "resume_text": provided.resume_text or (_resume_to_text(resume) if resume is not None else None),
        "project_summaries": _dedupe_strings(project_summaries),
        "tags": _dedupe_strings(tags),
        "extracted_skills": _dedupe_strings(extracted_skills),
        "repository_history_summary": _dedupe_strings(history_summaries),
        "repository_file_evidence": file_evidence,
        "collaboration_signals": [],
    }

    user_profile["collaboration_signals"] = _dedupe_strings(
        collaboration_signals
        + _derive_collaboration_signals(
            project_summaries=user_profile["project_summaries"],
            tags=user_profile["tags"],
            repository_history_summary=user_profile["repository_history_summary"],
            repository_file_evidence=user_profile["repository_file_evidence"],
        )
    )

    if not any(
        [
            user_profile["resume_text"],
            user_profile["project_summaries"],
            user_profile["tags"],
            user_profile["extracted_skills"],
            user_profile["repository_history_summary"],
            user_profile["repository_file_evidence"],
            user_profile["collaboration_signals"],
        ]
    ):
        raise ValueError("No user evidence was available to analyze")
    return user_profile


def _deployment_name() -> str | None:
    # This should point at a GPT-4o mini deployment when configured.
    return (os.environ.get("AZURE_OPENAI_JOB_READINESS_DEPLOYMENT") or "").strip() or None


def _configured_deployment_name() -> str | None:
    return _deployment_name() or (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip() or None


def _missing_azure_configuration_message() -> str:
    missing = [
        env_name
        for env_name in (
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_API_VERSION",
        )
        if not (os.environ.get(env_name) or "").strip()
    ]
    if _configured_deployment_name() is None:
        missing.append("AZURE_OPENAI_JOB_READINESS_DEPLOYMENT or AZURE_OPENAI_DEPLOYMENT")
    return (
        "Job readiness analysis is unavailable because Azure OpenAI is not fully configured. "
        f"Missing: {', '.join(missing)}."
    )


def _parse_job_readiness_payload(
    payload: dict[str, Any] | None,
) -> tuple[JobReadinessResult | None, str | None]:
    if payload is None:
        return None, (
            "Azure OpenAI did not return a structured response for job readiness analysis. "
            "Check backend logs for HTTP, timeout, quota, or parsing errors."
        )
    try:
        result = JobReadinessResult.model_validate(payload)
    except ValidationError:
        return None, (
            "Azure OpenAI returned a structured response, but it did not match the expected "
            "job readiness schema."
        )

    if not _suggestions_are_actionable(result):
        return None, (
            "Azure OpenAI returned job readiness suggestions, but they did not pass the backend "
            "actionability checks."
        )
    return result, None


def analyze_job_readiness_with_diagnostics(
    *,
    job_description: str,
    user_profile: dict[str, Any],
    max_attempts: int = 2,
) -> JobReadinessAnalysisOutcome:
    if not azure_openai_enabled():
        return JobReadinessAnalysisOutcome(
            result=None,
            error_message=(
                "Job readiness analysis is unavailable because Azure OpenAI is disabled. "
                "Set ARTIFACT_MINER_ML_PROVIDER=azure_openai."
            ),
        )

    user_prompt = render_job_readiness_user_prompt(job_description, user_profile)
    last_error = None
    active_deployment = _configured_deployment_name()
    for attempt in range(max_attempts):
        payload = azure_chat_json(
            system_prompt=JOB_READINESS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=JOB_READINESS_RESPONSE_SCHEMA,
            schema_name=DEFAULT_JOB_READINESS_SCHEMA_NAME,
            max_tokens=420,
            temperature=0.0,
            deployment=_deployment_name(),
        )
        result, error_message = _parse_job_readiness_payload(payload)
        if result is not None:
            return JobReadinessAnalysisOutcome(result=result)

        if payload is None and last_error is None and any(
            not (os.environ.get(env_name) or "").strip()
            for env_name in (
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_API_KEY",
                "AZURE_OPENAI_API_VERSION",
            )
        ):
            error_message = _missing_azure_configuration_message()

        last_error = error_message
        logger.warning(
            "Job readiness analysis attempt %s/%s failed using deployment=%s: %s",
            attempt + 1,
            max_attempts,
            active_deployment,
            error_message,
        )

    return JobReadinessAnalysisOutcome(
        result=None,
        error_message=last_error
        or "Job readiness analysis failed after repeated Azure OpenAI attempts.",
    )


def run_job_readiness_analysis(
    *,
    job_description: str,
    user_profile: dict[str, Any],
    max_attempts: int = 2,
) -> JobReadinessResult | None:
    return analyze_job_readiness_with_diagnostics(
        job_description=job_description,
        user_profile=user_profile,
        max_attempts=max_attempts,
    ).result
