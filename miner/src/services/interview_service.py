from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlmodel import Session

from src.core.ML.models.azure_openai_runtime import azure_chat_json, azure_openai_enabled
from src.core.ML.models.interview_constants import (
    DEFAULT_INTERVIEW_ANSWER_SCHEMA_NAME,
    DEFAULT_INTERVIEW_DIMENSIONS_SCHEMA_NAME,
    DEFAULT_INTERVIEW_PROJECT_SCHEMA_NAME,
    DEFAULT_INTERVIEW_START_SCHEMA_NAME,
    INTERVIEW_ANSWER_RESPONSE_SCHEMA,
    INTERVIEW_ANSWER_SYSTEM_PROMPT,
    INTERVIEW_ANSWER_USER_PROMPT_TEMPLATE,
    INTERVIEW_DIMENSIONS_RESPONSE_SCHEMA,
    INTERVIEW_DIMENSIONS_SYSTEM_PROMPT,
    INTERVIEW_DIMENSIONS_USER_PROMPT_TEMPLATE,
    INTERVIEW_PROJECT_SELECTION_RESPONSE_SCHEMA,
    INTERVIEW_PROJECT_SELECTION_SYSTEM_PROMPT,
    INTERVIEW_PROJECT_SELECTION_USER_PROMPT_TEMPLATE,
    INTERVIEW_START_RESPONSE_SCHEMA,
    INTERVIEW_START_SYSTEM_PROMPT,
    INTERVIEW_START_USER_PROMPT_TEMPLATE,
)
from src.database.api.CRUD.projects import get_all_project_ids, get_project_report_models_by_names
from src.database.api.models import ProjectReportModel
from src.infrastructure.log.logging import get_logger
from src.services.job_readiness_service import (
    JobReadinessUserProfileInput,
    _project_file_signal_summary,
    _project_skills_from_stats,
    _project_stat_summary_lines,
    _project_summary,
    _project_tags_from_stats,
    build_user_profile,
    run_job_readiness_analysis,
)


InterviewQuestionCategory = Literal["project_based", "role_specific", "skill_gap"]
InterviewAction = Literal["retry_same_question", "advance_dimension", "probe_gap"]
MAX_QUESTIONS_PER_DIMENSION = 2

logger = get_logger(__name__)


class InterviewStartResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    question_category: InterviewQuestionCategory
    interviewer_focus: str = Field(min_length=1)
    fit_dimension: str = Field(min_length=1)
    project_name: str | None = None
    next_action: InterviewAction = "advance_dimension"


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
    fit_dimension: str = Field(min_length=1)
    project_name: str | None = None
    next_action: InterviewAction


_DIMENSION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "api_design": ("rest api", "rest", "api", "endpoint", "service", "backend"),
    "database": ("sql", "database", "postgresql", "mysql", "query", "schema"),
    "testing": ("test", "testing", "unit test", "integration test", "pytest"),
    "performance": ("performance", "optimize", "latency", "response time", "query efficiency"),
    "reliability": ("reliability", "observability", "debug", "error handling", "monitoring"),
    "architecture": ("architecture", "design", "tradeoff", "layer", "service layer"),
    "collaboration": ("collaborate", "stakeholder", "frontend", "code review", "git"),
    "deployment": ("docker", "deployment", "container", "ci/cd", "pipeline"),
    "cloud": ("azure", "aws", "cloud"),
    "scalability": ("scalable", "scalability", "high-traffic", "throughput"),
}

_DIMENSION_LABELS: dict[str, str] = {
    "api_design": "API design",
    "database": "database design and query reasoning",
    "testing": "testing strategy",
    "performance": "performance optimization",
    "reliability": "reliability and debugging",
    "architecture": "architecture and tradeoffs",
    "collaboration": "collaboration and engineering workflow",
    "deployment": "deployment readiness",
    "cloud": "cloud/platform readiness",
    "scalability": "scalability reasoning",
}

_ROLE_LENS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "consulting_business": (
        "consultant", "consulting", "client", "stakeholder", "business", "workflow",
        "recommendation", "requirements", "operations", "adoption", "process",
    ),
    "product_strategy": (
        "product", "roadmap", "prioritization", "user", "customer", "strategy",
        "feature prioritization", "market",
    ),
    "data_analysis": (
        "analysis", "analytics", "dashboard", "reporting", "insight", "visualization",
        "business intelligence", "decision-making", "data-driven",
    ),
    "engineering_delivery": (
        "backend", "frontend", "engineer", "engineering", "api", "database", "testing",
        "performance", "reliability", "deployment", "software",
    ),
}

_ROLE_TOOL_HINTS: dict[str, tuple[str, ...]] = {
    "product_strategy": ("jira", "confluence", "figma", "notion"),
    "consulting_business": ("jira", "confluence", "excel", "power bi", "tableau"),
    "data_analysis": ("sql", "python", "tableau", "power bi", "excel", "matplotlib"),
    "engineering_delivery": ("docker", "fastapi", "postgresql", "mysql", "pytest", "github actions"),
}

_ROLE_PROJECT_SIGNALS: dict[str, tuple[str, ...]] = {
    "consulting_business": (
        "dashboard", "report", "reporting", "analytics", "stakeholder", "workflow", "communication",
        "presentation", "insight", "business",
    ),
    "product_strategy": (
        "dashboard", "ui", "ux", "user", "mobile", "web", "feedback", "iteration", "feature", "portal",
    ),
    "data_analysis": (
        "data", "analytics", "visualization", "report", "reporting", "sql", "insight", "pipeline", "dashboard",
    ),
    "engineering_delivery": (
        "api", "backend", "service", "testing", "deployment", "fastapi", "database", "reliability",
    ),
}


class InterviewDimensionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensions: list[dict[str, Any]]


def _deployment_name() -> str | None:
    return (os.environ.get("AZURE_OPENAI_INTERVIEW_DEPLOYMENT") or "").strip() or None


def _tokenize_lower(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9+/.-]*", text.lower())


def _infer_role_lens(job_description: str) -> str:
    lowered = job_description.lower()
    scores: list[tuple[int, str]] = []
    for lens, keywords in _ROLE_LENS_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        scores.append((score, lens))
    scores.sort(reverse=True)
    best_score, best_lens = scores[0]
    return best_lens if best_score > 0 else "general_professional"


def _clean_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _dimension_counts(values: list[str] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values or []:
        key = str(value or "").strip()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


def _fit_context(interview_context: dict[str, Any]) -> dict[str, Any]:
    return interview_context.get("job_fit_context", {})


def _project_tech_stack(project: ProjectReportModel) -> list[str]:
    values: list[str] = []
    values.extend(_clean_list(list(project.showcase_frameworks or [])))
    values.extend(_clean_list(_project_skills_from_stats(project)))
    values.extend(_clean_list(_project_tags_from_stats(project)))
    return _clean_list(values)


def _project_evidence_blob(project: ProjectReportModel) -> str:
    parts: list[str] = []
    parts.append(_project_summary(project))
    parts.extend(_project_stat_summary_lines(project.statistic))
    parts.extend(_project_file_signal_summary(project))
    parts.extend(_project_tech_stack(project))
    return "\n".join(_clean_list(parts)).lower()


def _extract_job_dimensions(job_description: str) -> list[dict[str, Any]]:
    lowered = job_description.lower()
    scored: list[dict[str, Any]] = []
    for dimension, keywords in _DIMENSION_KEYWORDS.items():
        matches = [keyword for keyword in keywords if keyword in lowered]
        if matches:
            scored.append(
                {
                    "dimension": dimension,
                    "label": _DIMENSION_LABELS[dimension],
                    "matches": matches,
                    "priority": len(matches),
                }
            )

    if not scored:
        scored.append(
            {
                "dimension": "architecture",
                "label": _DIMENSION_LABELS["architecture"],
                "matches": [],
                "priority": 1,
            }
        )

    scored.sort(key=lambda item: (-int(item["priority"]), str(item["dimension"])))
    return scored


def _normalize_dimension_id(value: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return raw or "general_fit"


def _parse_dimension_payload(payload: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if payload is None:
        logger.warning("[TASK=INTERVIEW_DIMENSIONS] Azure returned no payload")
        return None
    try:
        parsed = InterviewDimensionSet.model_validate(payload)
    except ValidationError as exc:
        logger.warning(
            "[TASK=INTERVIEW_DIMENSIONS] Payload failed validation: %s | payload=%s",
            exc,
            json.dumps(payload, ensure_ascii=True)[:1600],
        )
        return None

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(parsed.dimensions, start=1):
        dimension_id = _normalize_dimension_id(str(item.get("dimension_id", "")))
        label = str(item.get("label", "")).strip() or dimension_id.replace("_", " ")
        reason = str(item.get("reason", "")).strip() or f"Assess fit for {label}."
        signals = _clean_list([str(signal) for signal in item.get("signals", [])])[:6]
        preferred = str(item.get("preferred_question_category", "project_based")).strip()
        if preferred not in {"project_based", "role_specific", "skill_gap"}:
            preferred = "project_based"
        normalized.append(
            {
                "dimension": dimension_id,
                "label": label,
                "matches": signals,
                "priority": int(item.get("priority", index)),
                "reason": reason,
                "preferred_question_category": preferred,
            }
        )

    normalized.sort(key=lambda entry: (int(entry["priority"]), str(entry["dimension"])))
    return normalized


def _heuristic_dimension_entries(job_description: str) -> list[dict[str, Any]]:
    scored = _extract_job_dimensions(job_description)
    out: list[dict[str, Any]] = []
    for item in scored:
        dimension = str(item["dimension"])
        out.append(
            {
                "dimension": dimension,
                "label": str(item["label"]),
                "matches": list(item.get("matches", [])),
                "priority": int(item.get("priority", 1)),
                "reason": f"This role appears to value {item['label']}.",
                "preferred_question_category": "project_based",
            }
        )
    return out


def _role_lens_guardrail(
    *,
    role_lens: str,
    dimensions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if role_lens != "consulting_business":
        return dimensions

    consulting_tokens = {"business", "stakeholder", "client", "recommendation", "workflow", "communication"}
    has_consulting_dimension = any(
        any(token in f"{item.get('label', '')} {item.get('reason', '')}".lower() for token in consulting_tokens)
        for item in dimensions
    )
    if has_consulting_dimension:
        return dimensions

    guardrail = {
        "dimension": "business_problem_framing",
        "label": "business problem framing and stakeholder communication",
        "matches": ["business problem", "stakeholder needs", "recommendation", "workflow improvement"],
        "priority": 1,
        "reason": "This consulting-oriented role should assess how the candidate explains technical work in business and stakeholder terms.",
        "preferred_question_category": "project_based",
    }
    shifted: list[dict[str, Any]] = [guardrail]
    for index, item in enumerate(dimensions, start=2):
        updated = dict(item)
        updated["priority"] = max(index, int(item.get("priority", index)))
        shifted.append(updated)
    return shifted[:7]


def derive_interview_dimensions(
    *,
    job_description: str,
    user_profile: dict[str, Any],
    readiness_signals: dict[str, Any],
    max_attempts: int = 2,
) -> list[dict[str, Any]]:
    role_lens = _infer_role_lens(job_description)
    if not azure_openai_enabled():
        return _role_lens_guardrail(
            role_lens=role_lens,
            dimensions=_heuristic_dimension_entries(job_description),
        )

    user_prompt = (
        INTERVIEW_DIMENSIONS_USER_PROMPT_TEMPLATE
        .replace("{{job_description}}", job_description)
        .replace("{{user_profile}}", json.dumps(user_profile, indent=2, sort_keys=True))
        .replace("{{job_readiness_signals}}", json.dumps(readiness_signals, indent=2, sort_keys=True))
    )
    for attempt in range(max_attempts):
        payload = azure_chat_json(
            system_prompt=INTERVIEW_DIMENSIONS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=INTERVIEW_DIMENSIONS_RESPONSE_SCHEMA,
            schema_name=DEFAULT_INTERVIEW_DIMENSIONS_SCHEMA_NAME,
            max_tokens=700,
            temperature=0.1,
            deployment=_deployment_name(),
        )
        dimensions = _parse_dimension_payload(payload)
        if dimensions:
            return _role_lens_guardrail(role_lens=role_lens, dimensions=dimensions)
        logger.warning(
            "[TASK=INTERVIEW_DIMENSIONS] Attempt %d returned no valid structured dimensions",
            attempt + 1,
        )
    return _role_lens_guardrail(
        role_lens=role_lens,
        dimensions=_heuristic_dimension_entries(job_description),
    )


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


def _project_fit_entry(
    project: ProjectReportModel,
    dimensions: list[dict[str, Any]],
    *,
    role_lens: str,
    job_description: str,
) -> dict[str, Any]:
    evidence_blob = _project_evidence_blob(project)
    matched_dimensions: list[str] = []
    score = 0
    for item in dimensions:
        dimension = str(item["dimension"])
        dimension_matches = [
            keyword
            for keyword in item["matches"]
            if keyword in evidence_blob
        ]
        label_tokens = _tokenize_lower(f"{item.get('label', '')} {item.get('reason', '')}")
        overlap = [
            token for token in label_tokens
            if len(token) > 3 and token in evidence_blob
        ]
        if dimension_matches:
            matched_dimensions.append(dimension)
            score += len(dimension_matches) * 3
        elif overlap:
            matched_dimensions.append(dimension)
            score += min(len(overlap), 2)

    tech_stack = _project_tech_stack(project)
    score += min(len(tech_stack), 6)

    if project.showcase_title:
        score += 1
    if project.showcase_bullet_points:
        score += min(len(project.showcase_bullet_points), 3)

    role_hits = [
        signal for signal in _ROLE_PROJECT_SIGNALS.get(role_lens, ())
        if signal in evidence_blob and signal in job_description.lower()
    ]
    score += len(role_hits) * 4

    title_blob = f"{project.project_name} {project.showcase_title or ''}".lower()
    if role_lens in {"product_strategy", "consulting_business", "data_analysis"}:
        if any(token in title_blob for token in ("portal", "dashboard", "analytics", "habit", "mobile")):
            score += 5
    if role_lens == "engineering_delivery":
        if any(token in title_blob for token in ("service", "api", "backend", "orders")):
            score += 5

    return {
        "project_name": project.project_name,
        "summary": _project_summary(project),
        "tech_stack": tech_stack[:10],
        "evidence_points": _clean_list(
            [str(_project_summary(project))]
            + _project_stat_summary_lines(project.statistic)[:4]
            + list(project.showcase_bullet_points or [])[:4]
        )[:8],
        "matched_dimensions": _clean_list(matched_dimensions),
        "role_hits": _clean_list(role_hits)[:8],
        "fit_score": score,
    }


def _derive_allowed_tools(
    *,
    job_description: str,
    role_lens: str,
    project_entries: list[dict[str, Any]],
    readiness_signals: dict[str, Any],
) -> list[str]:
    allowed: list[str] = []
    job_text = job_description.lower()

    for entry in project_entries:
        allowed.extend([str(value) for value in entry.get("tech_stack", [])])

    for weakness in readiness_signals.get("weaknesses", []):
        if not isinstance(weakness, dict):
            continue
        allowed.extend(_tokenize_lower(f"{weakness.get('item', '')} {weakness.get('reason', '')}"))

    allowed.extend(list(_ROLE_TOOL_HINTS.get(role_lens, ())))

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in allowed:
        value = str(raw or "").strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered not in job_text and lowered not in json.dumps(project_entries, ensure_ascii=True).lower():
            if lowered not in {"docker", "jira", "confluence", "tableau", "power bi", "figma", "pytest"}:
                continue
            if lowered not in job_text:
                continue
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(value)
    return normalized[:10]


def _derive_job_fit_context(
    *,
    job_description: str,
    projects: list[ProjectReportModel],
    dimensions: list[dict[str, Any]],
    readiness_signals: dict[str, Any],
    role_lens: str,
) -> dict[str, Any]:
    prioritized_dimensions = dimensions
    project_entries = [
        _project_fit_entry(
            project,
            prioritized_dimensions,
            role_lens=role_lens,
            job_description=job_description,
        )
        for project in projects
    ]
    project_entries.sort(key=lambda item: (-int(item["fit_score"]), item["project_name"]))

    weak_dimensions: list[str] = []
    for weakness in readiness_signals.get("weaknesses", []):
        if not isinstance(weakness, dict):
            continue
        text = f"{weakness.get('item', '')} {weakness.get('reason', '')}".lower()
        for dimension, keywords in _DIMENSION_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                weak_dimensions.append(dimension)

    return {
        "prioritized_dimensions": prioritized_dimensions,
        "relevant_projects": project_entries[:5],
        "primary_project": project_entries[0]["project_name"] if project_entries else None,
        "weak_dimensions": _clean_list(weak_dimensions),
        "role_lens": role_lens,
        "allowed_tools": _derive_allowed_tools(
            job_description=job_description,
            role_lens=role_lens,
            project_entries=project_entries[:5],
            readiness_signals=readiness_signals,
        ),
    }


def build_interview_context(
    *,
    session: Session,
    job_description: str,
    resume_id: int | None = None,
    project_names: list[str] | None = None,
    user_profile_input: JobReadinessUserProfileInput | None = None,
) -> dict[str, Any]:
    selected_project_names = list(project_names or [])
    if resume_id is None and not selected_project_names:
        selected_project_names = get_all_project_ids(session)

    user_profile = build_user_profile(
        session=session,
        resume_id=resume_id,
        project_names=selected_project_names,
        user_profile_input=user_profile_input,
    )
    projects = get_project_report_models_by_names(session, selected_project_names) if selected_project_names else []
    readiness_signals = _readiness_signals(
        job_description=job_description,
        user_profile=user_profile,
    )
    dimensions = derive_interview_dimensions(
        job_description=job_description,
        user_profile=user_profile,
        readiness_signals=readiness_signals,
    )
    role_lens = _infer_role_lens(job_description)

    return {
        "user_profile": user_profile,
        "job_readiness_signals": readiness_signals,
        "job_fit_context": _derive_job_fit_context(
            job_description=job_description,
            projects=projects,
            dimensions=dimensions,
            readiness_signals=readiness_signals,
            role_lens=role_lens,
        ),
    }


def _find_project_entry(interview_context: dict[str, Any], project_name: str | None) -> dict[str, Any] | None:
    if not project_name:
        return None
    for entry in _fit_context(interview_context).get("relevant_projects", []):
        if isinstance(entry, dict) and entry.get("project_name") == project_name:
            return entry
    return None


def _select_fit_dimension(
    interview_context: dict[str, Any],
    *,
    covered_dimensions: list[str] | None = None,
    current_fit_dimension: str | None = None,
    prefer_gap: bool = False,
) -> str:
    counts = _dimension_counts(covered_dimensions)

    if current_fit_dimension and counts.get(current_fit_dimension, 0) < MAX_QUESTIONS_PER_DIMENSION:
        return current_fit_dimension

    covered = {str(value) for value in (covered_dimensions or [])}
    fit_context = _fit_context(interview_context)
    weak_dimensions = [str(value) for value in fit_context.get("weak_dimensions", [])]
    prioritized = fit_context.get("prioritized_dimensions", [])

    if prefer_gap:
        for dimension in weak_dimensions:
            if dimension not in covered:
                return dimension

    for item in prioritized:
        dimension = str(item.get("dimension", "")).strip()
        if dimension and dimension not in covered:
            return dimension

    if prioritized:
        return str(prioritized[0].get("dimension", "architecture"))
    return "architecture"


def _select_next_dimension(
    interview_context: dict[str, Any],
    *,
    current_fit_dimension: str | None,
    covered_dimensions: list[str] | None = None,
    prefer_gap: bool = False,
) -> str:
    counts = _dimension_counts(covered_dimensions)
    fit_context = _fit_context(interview_context)
    prioritized = fit_context.get("prioritized_dimensions", [])

    if prefer_gap:
        for dimension in [str(value) for value in fit_context.get("weak_dimensions", [])]:
            if dimension != current_fit_dimension and counts.get(dimension, 0) < MAX_QUESTIONS_PER_DIMENSION:
                return dimension

    for item in prioritized:
        dimension = str(item.get("dimension", "")).strip()
        if not dimension or dimension == current_fit_dimension:
            continue
        if counts.get(dimension, 0) < MAX_QUESTIONS_PER_DIMENSION:
            return dimension

    return _select_fit_dimension(
        interview_context,
        covered_dimensions=covered_dimensions,
        current_fit_dimension=None,
        prefer_gap=prefer_gap,
    )


def _select_project_for_dimension(
    interview_context: dict[str, Any],
    fit_dimension: str,
    *,
    current_project_name: str | None = None,
    job_description: str | None = None,
) -> str | None:
    if current_project_name:
        return current_project_name

    fit_context = _fit_context(interview_context)
    relevant_projects = [
        entry for entry in fit_context.get("relevant_projects", [])
        if isinstance(entry, dict)
    ]
    candidates = [
        entry for entry in relevant_projects
        if fit_dimension in entry.get("matched_dimensions", [])
    ]
    if not candidates:
        candidates = relevant_projects[:3]

    if not candidates:
        primary = fit_context.get("primary_project")
        return str(primary) if primary else None

    if len(candidates) == 1 or not azure_openai_enabled() or not job_description:
        return str(candidates[0].get("project_name"))

    chosen = _choose_project_with_model(
        job_description=job_description,
        role_lens=str(fit_context.get("role_lens", "general_professional")),
        fit_dimension=fit_dimension,
        candidates=candidates[:4],
    )
    if chosen:
        valid_names = {str(entry.get("project_name")) for entry in candidates}
        if chosen in valid_names:
            role_lens = str(fit_context.get("role_lens", "general_professional"))
            if role_lens in {"product_strategy", "consulting_business", "data_analysis"}:
                chosen_entry = next((entry for entry in candidates if entry.get("project_name") == chosen), None)
                best_role_entry = max(
                    candidates,
                    key=lambda entry: (
                        len(entry.get("role_hits", [])),
                        int(entry.get("fit_score", 0)),
                    ),
                )
                if chosen_entry and best_role_entry:
                    chosen_role_hits = len(chosen_entry.get("role_hits", []))
                    best_role_hits = len(best_role_entry.get("role_hits", []))
                    if best_role_hits > chosen_role_hits:
                        return str(best_role_entry.get("project_name"))
            return chosen

    primary = fit_context.get("primary_project")
    if primary:
        for entry in candidates:
            if entry.get("project_name") == primary:
                return str(primary)
    return str(candidates[0].get("project_name"))


def _choose_project_with_model(
    *,
    job_description: str,
    role_lens: str,
    fit_dimension: str,
    candidates: list[dict[str, Any]],
    max_attempts: int = 2,
) -> str | None:
    candidate_payload = [
        {
            "project_name": entry.get("project_name"),
            "summary": entry.get("summary"),
            "tech_stack": entry.get("tech_stack", []),
            "evidence_points": entry.get("evidence_points", []),
            "matched_dimensions": entry.get("matched_dimensions", []),
            "role_hits": entry.get("role_hits", []),
        }
        for entry in candidates
    ]
    user_prompt = (
        INTERVIEW_PROJECT_SELECTION_USER_PROMPT_TEMPLATE
        .replace("{{job_description}}", job_description)
        .replace("{{role_lens}}", role_lens)
        .replace("{{fit_dimension}}", fit_dimension)
        .replace("{{candidate_projects}}", json.dumps(candidate_payload, indent=2, sort_keys=True))
    )
    for attempt in range(max_attempts):
        payload = azure_chat_json(
            system_prompt=INTERVIEW_PROJECT_SELECTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=INTERVIEW_PROJECT_SELECTION_RESPONSE_SCHEMA,
            schema_name=DEFAULT_INTERVIEW_PROJECT_SCHEMA_NAME,
            max_tokens=220,
            temperature=0.1,
            deployment=_deployment_name(),
        )
        project_name = str((payload or {}).get("project_name", "")).strip() if isinstance(payload, dict) else ""
        if project_name:
            return project_name
    return None


def _render_interview_prompt(
    *,
    template: str,
    job_description: str,
    prompt_context: dict[str, Any],
    current_question: str = "",
    user_answer: str = "",
) -> str:
    prompt = (
        template
        .replace("{{job_description}}", job_description)
        .replace("{{interview_context}}", json.dumps(prompt_context, indent=2, sort_keys=True))
    )
    if current_question:
        prompt = prompt.replace("{{current_question}}", current_question)
    if user_answer:
        prompt = prompt.replace("{{user_answer}}", user_answer)
    return prompt


def _render_prompt_context(
    *,
    interview_context: dict[str, Any],
    fit_dimension: str,
    project_name: str | None,
    covered_dimensions: list[str] | None = None,
    retry_same_question: bool = False,
) -> dict[str, Any]:
    project_entry = _find_project_entry(interview_context, project_name)
    fit_context = _fit_context(interview_context)
    prioritized = fit_context.get("prioritized_dimensions", [])
    selected_dimension = next(
        (item for item in prioritized if item.get("dimension") == fit_dimension),
        {"dimension": fit_dimension, "label": _DIMENSION_LABELS.get(fit_dimension, fit_dimension), "matches": []},
    )
    active_project_evidence = {
        "project_name": project_entry.get("project_name") if project_entry else project_name,
        "summary": project_entry.get("summary") if project_entry else None,
        "tech_stack": list(project_entry.get("tech_stack", []))[:8] if project_entry else [],
        "evidence_points": list(project_entry.get("evidence_points", []))[:6] if project_entry else [],
    }
    allowed_example_points = _clean_list(
        list(active_project_evidence.get("evidence_points", []))
        + [str(selected_dimension.get("label", ""))]
        + [str(match) for match in selected_dimension.get("matches", [])]
    )[:8]
    return {
        "job_fit_context": fit_context,
        "role_lens": fit_context.get("role_lens", "general_professional"),
        "active_project": project_entry,
        "active_project_evidence": active_project_evidence,
        "active_fit_dimension": {
            "dimension": fit_dimension,
            "label": selected_dimension.get("label", _DIMENSION_LABELS.get(fit_dimension, fit_dimension)),
            "job_matches": selected_dimension.get("matches", []),
            "reason": selected_dimension.get("reason", ""),
            "preferred_question_category": selected_dimension.get("preferred_question_category", "project_based"),
        },
        "allowed_example_points": allowed_example_points,
        "allowed_tools": list(fit_context.get("allowed_tools", [])),
        "covered_dimensions": list(covered_dimensions or []),
        "dimension_counts": _dimension_counts(covered_dimensions),
        "retry_same_question": retry_same_question,
        "user_profile": interview_context.get("user_profile", {}),
        "job_readiness_signals": interview_context.get("job_readiness_signals", {}),
    }


def render_interview_start_prompt(
    *,
    job_description: str,
    interview_context: dict[str, Any],
    fit_dimension: str,
    project_name: str | None,
) -> str:
    return _render_interview_prompt(
        template=INTERVIEW_START_USER_PROMPT_TEMPLATE,
        job_description=job_description,
        prompt_context=_render_prompt_context(
            interview_context=interview_context,
            fit_dimension=fit_dimension,
            project_name=project_name,
        ),
    )


def render_interview_answer_prompt(
    *,
    job_description: str,
    interview_context: dict[str, Any],
    current_question: str,
    user_answer: str,
    fit_dimension: str,
    project_name: str | None,
    covered_dimensions: list[str] | None = None,
    retry_same_question: bool = False,
) -> str:
    return _render_interview_prompt(
        template=INTERVIEW_ANSWER_USER_PROMPT_TEMPLATE,
        job_description=job_description,
        prompt_context=_render_prompt_context(
            interview_context=interview_context,
            fit_dimension=fit_dimension,
            project_name=project_name,
            covered_dimensions=covered_dimensions,
            retry_same_question=retry_same_question,
        ),
        current_question=current_question,
        user_answer=user_answer,
    )


def _repair_start_payload(
    payload: dict[str, Any],
    *,
    fit_dimension: str,
    project_name: str | None,
) -> dict[str, Any]:
    if not str(payload.get("fit_dimension", "")).strip():
        payload["fit_dimension"] = fit_dimension
    if "project_name" not in payload:
        payload["project_name"] = project_name
    if not str(payload.get("next_action", "")).strip():
        payload["next_action"] = "advance_dimension"
    return payload


def _parse_start_payload(
    payload: dict[str, Any] | None,
    *,
    fit_dimension: str,
    project_name: str | None,
) -> InterviewStartResult | None:
    if payload is None:
        logger.warning("[TASK=INTERVIEW_START] Azure returned no payload")
        return None
    if isinstance(payload, dict):
        payload = _repair_start_payload(payload, fit_dimension=fit_dimension, project_name=project_name)
    try:
        return InterviewStartResult.model_validate(payload)
    except ValidationError as exc:
        logger.warning(
            "[TASK=INTERVIEW_START] Payload failed validation: %s | payload=%s",
            exc,
            json.dumps(payload, ensure_ascii=True)[:1200],
        )
        return None


def _repair_answer_payload(
    payload: dict[str, Any],
    *,
    fit_dimension: str,
    project_name: str | None,
) -> dict[str, Any]:
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
    if not str(payload.get("fit_dimension", "")).strip():
        payload["fit_dimension"] = fit_dimension
    if "project_name" not in payload:
        payload["project_name"] = project_name
    if not str(payload.get("next_action", "")).strip():
        payload["next_action"] = "advance_dimension" if payload.get("answer_acceptable") else "retry_same_question"
    return payload


def _ground_example_answer(
    example_answer: str,
    *,
    user_answer: str,
    project_entry: dict[str, Any] | None,
    allowed_tools: list[str] | None = None,
    allowed_example_points: list[str] | None = None,
) -> str:
    cleaned = " ".join(str(example_answer or "").split()).strip()
    if not cleaned:
        return cleaned

    lowered = cleaned.lower()
    allowed_text = " ".join(
        [
            str(user_answer or ""),
            json.dumps(project_entry or {}, ensure_ascii=True),
            json.dumps(allowed_example_points or [], ensure_ascii=True),
            json.dumps(allowed_tools or [], ensure_ascii=True),
        ]
    ).lower()
    candidate_tools = [
        "jira",
        "confluence",
        "figma",
        "notion",
        "docker",
        "pytest",
        "prometheus",
        "grafana",
        "tableau",
        "power bi",
        "excel",
        "pandas",
        "matplotlib",
        "postgresql",
        "mysql",
        "github actions",
    ]
    disallowed_tools = [
        tool for tool in candidate_tools
        if tool in lowered and tool not in allowed_text
    ]
    banned_phrases = [
        "i used pytest",
        "pytest alongside",
        "kubernetes",
        "caching",
        "metrics",
        "latency",
        "throughput",
    ]
    if disallowed_tools or any(phrase in lowered and phrase not in allowed_text for phrase in banned_phrases):
        return (
            "A stronger answer would stay specific about the project context, explain the main decision or collaboration step, "
            "describe one concrete challenge, and connect the outcome back to the project goals without adding unsupported details."
        )
    return cleaned


def _is_non_answer(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return normalized in {
        "yes", "no", "idk", "i dont know", "i don't know", "not sure",
        "i am not sure", "i'm not sure", "maybe", "n/a",
    }


def _question_keywords(question: str) -> set[str]:
    stopwords = {
        "the", "and", "with", "that", "this", "from", "your", "what", "when", "where", "which",
        "have", "about", "into", "they", "them", "their", "while", "during", "would", "could",
        "project", "describe", "explain", "specific", "instance", "faced", "used",
    }
    return {
        token for token in _tokenize_lower(question)
        if len(token) > 3 and token not in stopwords
    }


def _should_accept_borderline_answer(
    *,
    user_answer: str,
    current_question: str,
    project_entry: dict[str, Any] | None,
    result: InterviewAnswerResult,
) -> bool:
    if result.answer_acceptable:
        return False
    if _is_non_answer(user_answer):
        return False

    normalized = " ".join(user_answer.split())
    if len(normalized.split()) < 22:
        return False

    question_terms = _question_keywords(current_question)
    allowed_text = " ".join(
        [
            normalized.lower(),
            json.dumps(project_entry or {}, ensure_ascii=True).lower(),
        ]
    )
    overlap = [term for term in question_terms if term in normalized.lower() or term in allowed_text]
    concrete_markers = (
        "because", "so that", "to keep", "by ", "using", "through", "helped", "ensured",
        "aligned", "validated", "organized", "translated", "checked", "improved",
    )
    has_structure = any(marker in normalized.lower() for marker in concrete_markers)

    return len(overlap) >= 2 and has_structure


def _relax_answer_rejection(
    *,
    result: InterviewAnswerResult,
    user_answer: str,
    current_question: str,
    project_entry: dict[str, Any] | None,
) -> InterviewAnswerResult:
    if not _should_accept_borderline_answer(
        user_answer=user_answer,
        current_question=current_question,
        project_entry=project_entry,
        result=result,
    ):
        return result

    feedback = result.feedback.model_dump()
    feedback["strengths"] = (
        "Your answer was on-topic and specific enough to show a reasonable understanding of the project work."
    )
    feedback["improvements"] = (
        "To make the answer stronger, add one concrete example, outcome, or tool so the explanation feels more complete."
    )
    return InterviewAnswerResult.model_validate(
        {
            "answer_acceptable": True,
            "feedback": feedback,
            "next_question": result.next_question,
            "next_question_category": result.next_question_category,
            "fit_dimension": result.fit_dimension,
            "project_name": result.project_name,
            "next_action": "advance_dimension" if result.next_action == "retry_same_question" else result.next_action,
        }
    )


def _parse_answer_payload(
    payload: dict[str, Any] | None,
    *,
    fit_dimension: str,
    project_name: str | None,
    interview_context: dict[str, Any] | None = None,
    user_answer: str = "",
) -> InterviewAnswerResult | None:
    if payload is None:
        logger.warning("[TASK=INTERVIEW_ANSWER] Azure returned no payload")
        return None
    if isinstance(payload, dict):
        payload = _repair_answer_payload(payload, fit_dimension=fit_dimension, project_name=project_name)
        feedback = payload.get("feedback")
        if isinstance(feedback, dict):
            prompt_context = _render_prompt_context(
                interview_context=interview_context or {},
                fit_dimension=fit_dimension,
                project_name=project_name,
            )
            feedback["example_answer"] = _ground_example_answer(
                str(feedback.get("example_answer", "")),
                user_answer=user_answer,
                project_entry=_find_project_entry(interview_context or {}, project_name),
                allowed_tools=list(prompt_context.get("allowed_tools", [])),
                allowed_example_points=list(prompt_context.get("allowed_example_points", [])),
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
    current_fit_dimension: str | None = None,
    current_project_name: str | None = None,
    covered_dimensions: list[str] | None = None,
    prefer_gap: bool = False,
    max_attempts: int = 2,
) -> InterviewStartResult | None:
    if not azure_openai_enabled():
        logger.info("[TASK=INTERVIEW_START] Skipping generation because Azure OpenAI is disabled")
        return None

    fit_dimension = _select_fit_dimension(
        interview_context,
        covered_dimensions=covered_dimensions,
        current_fit_dimension=current_fit_dimension,
        prefer_gap=prefer_gap,
    )
    project_name = _select_project_for_dimension(
        interview_context,
        fit_dimension,
        current_project_name=current_project_name,
        job_description=job_description,
    )

    user_prompt = render_interview_start_prompt(
        job_description=job_description,
        interview_context=interview_context,
        fit_dimension=fit_dimension,
        project_name=project_name,
    )
    for attempt in range(max_attempts):
        payload = azure_chat_json(
            system_prompt=INTERVIEW_START_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=INTERVIEW_START_RESPONSE_SCHEMA,
            schema_name=DEFAULT_INTERVIEW_START_SCHEMA_NAME,
            max_tokens=360,
            temperature=0.2,
            deployment=_deployment_name(),
        )
        result = _parse_start_payload(payload, fit_dimension=fit_dimension, project_name=project_name)
        if result is not None:
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
    current_fit_dimension: str | None = None,
    current_project_name: str | None = None,
    covered_dimensions: list[str] | None = None,
    retry_same_question: bool = False,
    max_attempts: int = 2,
) -> InterviewAnswerResult | None:
    if not azure_openai_enabled():
        logger.info("[TASK=INTERVIEW_ANSWER] Skipping evaluation because Azure OpenAI is disabled")
        return None

    fit_dimension = _select_fit_dimension(
        interview_context,
        covered_dimensions=covered_dimensions,
        current_fit_dimension=current_fit_dimension,
        prefer_gap=False,
    )
    project_name = _select_project_for_dimension(
        interview_context,
        fit_dimension,
        current_project_name=current_project_name,
        job_description=job_description,
    )

    user_prompt = render_interview_answer_prompt(
        job_description=job_description,
        interview_context=interview_context,
        current_question=current_question,
        user_answer=user_answer,
        fit_dimension=fit_dimension,
        project_name=project_name,
        covered_dimensions=covered_dimensions,
        retry_same_question=retry_same_question,
    )
    for attempt in range(max_attempts):
        payload = azure_chat_json(
            system_prompt=INTERVIEW_ANSWER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=INTERVIEW_ANSWER_RESPONSE_SCHEMA,
            schema_name=DEFAULT_INTERVIEW_ANSWER_SCHEMA_NAME,
            max_tokens=800,
            temperature=0.2,
            deployment=_deployment_name(),
        )
        result = _parse_answer_payload(
            payload,
            fit_dimension=fit_dimension,
            project_name=project_name,
            interview_context=interview_context,
            user_answer=user_answer,
        )
        if result is not None:
            project_entry = _find_project_entry(interview_context, project_name)
            result = _relax_answer_rejection(
                result=result,
                user_answer=user_answer,
                current_question=current_question,
                project_entry=project_entry,
            )
            updated_history = list(covered_dimensions or [])
            if result.answer_acceptable and fit_dimension:
                updated_history.append(fit_dimension)
            current_count = _dimension_counts(updated_history).get(fit_dimension, 0)

            if (
                result.answer_acceptable
                and result.next_action != "retry_same_question"
                and result.fit_dimension == fit_dimension
                and current_count >= MAX_QUESTIONS_PER_DIMENSION
            ):
                next_dimension = _select_next_dimension(
                    interview_context,
                    current_fit_dimension=fit_dimension,
                    covered_dimensions=updated_history,
                    prefer_gap=result.next_action == "probe_gap",
                )
                next_project = _select_project_for_dimension(
                    interview_context,
                    next_dimension,
                    current_project_name=None,
                    job_description=job_description,
                )
                rotated = generate_question(
                    job_description=job_description,
                    interview_context=interview_context,
                    current_fit_dimension=next_dimension,
                    current_project_name=next_project,
                    covered_dimensions=updated_history,
                    prefer_gap=result.next_action == "probe_gap",
                    max_attempts=1,
                )
                if rotated is not None:
                    result = InterviewAnswerResult.model_validate(
                        {
                            "answer_acceptable": result.answer_acceptable,
                            "feedback": result.feedback.model_dump(),
                            "next_question": rotated.question,
                            "next_question_category": rotated.question_category,
                            "fit_dimension": rotated.fit_dimension,
                            "project_name": rotated.project_name,
                            "next_action": "advance_dimension",
                        }
                    )
            return result
        logger.warning(
            "[TASK=INTERVIEW_ANSWER] Attempt %d returned no valid structured evaluation",
            attempt + 1,
        )
    return None
