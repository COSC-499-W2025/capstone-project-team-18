"""
Standalone project summary builder used by the project card service.

This module provides build_project_summary(project_report) -> str | None,
extracted from the former ProjectSummariesSectionBuilder so the summary
logic is available outside of the portfolio section system.
"""
import os
import re

from src.core.statistic import ProjectStatCollection
from src.core.ML.models.contribution_analysis import (
    generate_project_summary,
    build_project_summary_facts,
    configure_project_summary_run,
)
from src.utils.data_processing import join_english
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _summary_diagnostics_enabled() -> bool:
    raw = os.environ.get("ARTIFACT_MINER_SUMMARY_DIAGNOSTICS", "0")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def build_project_summary(project_report) -> str | None:
    """
    Compose a 2-3 sentence grounded summary from project statistics.

    Attempts ML generation first (grounded by structured facts), then falls
    back to deterministic phrasing if ML is unavailable or fails.
    """
    facts = _build_project_summary_facts(project_report)
    if not facts:
        if _summary_diagnostics_enabled():
            logger.info(
                "[PROJECT_SUMMARY][%s] skipped: no facts extracted",
                getattr(project_report, "project_name", "unknown-project"),
            )
        return None

    require_ml = os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML") == "1"
    summary = generate_project_summary(facts)
    project_name = getattr(project_report, "project_name", "unknown-project")
    is_well_formed = bool(summary and _is_summary_well_formed(summary))
    goal_ok = stack_ok = contribution_ok = True
    covers_requirements = False
    if summary:
        goal_ok, stack_ok, contribution_ok = _summary_requirement_checks(summary, facts)
        covers_requirements = goal_ok and stack_ok and contribution_ok

    if summary and is_well_formed and (require_ml or covers_requirements):
        return summary

    if summary:
        logger.info(
            "Project summary rejected for %s "
            "(well_formed=%s, covers_requirements=%s, goal_ok=%s, stack_ok=%s, contribution_ok=%s)",
            project_name, is_well_formed, covers_requirements,
            goal_ok, stack_ok, contribution_ok,
        )

    if require_ml:
        return None

    fallback = _build_project_summary_deterministic(facts)
    if fallback and _is_summary_well_formed(fallback) and _summary_covers_requirements(fallback, facts):
        return fallback
    return None


def configure_summary_run(project_count: int) -> None:
    """Forward project count to the ML layer for batch configuration."""
    configure_project_summary_run(project_count)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_project_summary_facts(project_report) -> dict | None:
    project_name = getattr(project_report, "project_name", None)

    themes = project_report.get_value(ProjectStatCollection.PROJECT_THEMES.value) or []
    tags = project_report.get_value(ProjectStatCollection.PROJECT_TAGS.value) or []
    goal_terms = _select_goal_terms(project_name, themes, tags)

    frameworks = project_report.get_value(ProjectStatCollection.PROJECT_FRAMEWORKS.value)
    framework_names: list[str] = []
    if frameworks:
        ranked = sorted(frameworks, key=lambda ws: getattr(ws, "weight", 0), reverse=True)
        framework_names = [getattr(ws, "skill_name", str(ws)) for ws in ranked[:3]]
    stack_hints = _extract_stack_hints(themes, tags)
    for hint in stack_hints:
        if hint not in framework_names:
            framework_names.append(hint)
    framework_names = framework_names[:5]

    lang_ratio = project_report.get_value(ProjectStatCollection.CODING_LANGUAGE_RATIO.value)
    language_names: list[str] = []
    if lang_ratio:
        ranked_langs = sorted(lang_ratio.items(), key=lambda kv: kv[1], reverse=True)
        language_names = [getattr(lang, "value", str(lang)) for lang, _ in ranked_langs[:2]]

    role = project_report.get_value(ProjectStatCollection.COLLABORATION_ROLE.value)
    role_text = str(getattr(role, "value", role)) if role else None
    role_description = project_report.get_value(ProjectStatCollection.ROLE_DESCRIPTION.value)

    commit_dist = project_report.get_value(ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value)
    commit_focus = _top_commit_focus(commit_dist)
    commit_pct = project_report.get_value(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)
    line_pct = project_report.get_value(ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)
    activity_breakdown = _activity_breakdown(project_report)

    if not goal_terms and not framework_names and not language_names and not role_description and not activity_breakdown:
        return None

    return build_project_summary_facts(
        project_name=project_name,
        goal_terms=goal_terms,
        frameworks=framework_names,
        languages=language_names,
        stack_hints=stack_hints,
        role=role_text,
        commit_focus=commit_focus,
        commit_pct=commit_pct if isinstance(commit_pct, (int, float)) else None,
        line_pct=line_pct if isinstance(line_pct, (int, float)) else None,
        activity_breakdown=activity_breakdown,
        role_description=str(role_description).strip() if role_description else None,
    )


def _build_project_summary_deterministic(facts: dict) -> str | None:
    goal_terms = facts.get("goal_terms", [])
    frameworks = facts.get("frameworks", [])
    languages = facts.get("languages", [])
    role_description = facts.get("role_description")
    role = facts.get("role")
    commit_focus = facts.get("commit_focus")
    commit_pct = facts.get("commit_pct")
    line_pct = facts.get("line_pct")
    activity_breakdown = facts.get("activity_breakdown", [])
    allow_percentages = bool(facts.get("allow_percentages"))

    if goal_terms:
        top = goal_terms[:2]
        goal_sentence = (
            f"The project had a primary goal of {top[0]}."
            if len(top) == 1
            else f"The project had primary goals of {top[0]} and {top[1]}."
        )
    else:
        project_name = str(facts.get("project_name", "")).strip()
        goal_sentence = (
            f"The project targeted {project_name.replace('-', ' ').replace('_', ' ').lower()} outcomes."
            if project_name
            else "The project targeted a clearly scoped product outcome."
        )

    if frameworks and languages:
        stack_sentence = (
            f"It was implemented with {join_english(frameworks[:3])} and primarily written in "
            f"{join_english(languages[:2])}."
        )
    elif frameworks:
        stack_sentence = f"It was implemented with {join_english(frameworks[:3])}."
    elif languages:
        stack_sentence = f"It was primarily written in {join_english(languages[:2])}."
    else:
        stack_sentence = "The implementation stack was selected to match the project requirements."

    if role_description:
        contribution_sentence = role_description.rstrip(".") + "."
    else:
        contribution_sentence = _compose_contribution_sentence(
            role=role,
            commit_focus=commit_focus,
            commit_pct=commit_pct,
            line_pct=line_pct,
            activity_breakdown=activity_breakdown,
            allow_percentages=allow_percentages,
        )

    sentences = [s for s in [goal_sentence, stack_sentence, contribution_sentence] if s]
    if len(sentences) < 2:
        return None
    return " ".join(sentences[:3])


def _select_goal_terms(project_name: str | None, themes, tags) -> list[str]:
    project_tokens = _token_set(project_name or "")
    raw_terms = [str(x).strip() for x in list(themes) + list(tags) if str(x).strip()]
    deprioritize = {
        "ci", "cicd", "testing", "test", "configuration", "requirements", "known bugs",
        "startup scripts", "docker compose", "windows support", "macos support",
    }
    prioritize = {
        "student", "management", "records", "course", "itinerary", "trip", "event",
        "phonics", "pronunciation", "speech", "bayesian", "label", "transfer",
        "analysis", "dashboard", "visualization",
    }

    scored_terms: list[tuple[float, str, set[str]]] = []
    for term in raw_terms:
        term_tokens = _token_set(term)
        if not term_tokens:
            continue
        if project_tokens:
            overlap = len(term_tokens & project_tokens) / len(term_tokens)
            if overlap >= 0.6:
                continue
        score = 1.0
        if term_tokens & prioritize:
            score += 1.0
        if term_tokens & deprioritize:
            score -= 0.6
        if len(term_tokens) >= 2:
            score += 0.2
        scored_terms.append((score, term, term_tokens))

    scored_terms.sort(key=lambda x: x[0], reverse=True)

    selected: list[str] = []
    selected_tokens: list[set[str]] = []
    for _score, term, term_tokens in scored_terms:
        if any(_jaccard(term_tokens, existing) >= 0.6 for existing in selected_tokens):
            continue
        selected.append(term)
        selected_tokens.append(term_tokens)
        if len(selected) >= 4:
            break

    return selected[:4]


def _extract_stack_hints(themes, tags) -> list[str]:
    terms = [str(x).strip() for x in list(themes) + list(tags) if str(x).strip()]
    hints: list[str] = []
    seen: set[str] = set()
    tech_keywords = {
        "react", "next", "tailwind", "azure", "speech", "sdk", "android",
        "androidx", "typescript", "javascript", "python", "java", "docker",
        "pytest", "tkinter", "fastapi", "sql", "postgres", "mongodb",
    }
    for term in terms:
        token_set = _token_set(term)
        if not token_set or not (token_set & tech_keywords) or len(token_set) > 4:
            continue
        normalized = term.replace("next.js", "next").replace("typescript", "TypeScript").strip()
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        hints.append(normalized)
        if len(hints) >= 4:
            break
    return hints


def _activity_breakdown(project_report) -> list[tuple[str, float]]:
    activity = project_report.get_value(ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value)
    if not activity:
        return []
    pairs: list[tuple[str, float]] = []
    for domain, value in activity.items():
        name = str(getattr(domain, "value", domain)).replace("_", " ").lower()
        pct = float(value) * 100 if float(value) <= 1.0 else float(value)
        pairs.append((name, pct))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs


def _top_commit_focus(commit_dist) -> str | None:
    if not commit_dist:
        return None
    top = sorted(commit_dist.items(), key=lambda kv: kv[1], reverse=True)
    if not top:
        return None
    label = str(top[0][0]).replace("_", " ").strip().lower()
    return label if label else None


def _is_summary_well_formed(summary: str) -> bool:
    sentence_count = len([
        seg.strip()
        for seg in re.split(r"(?:(?<!\d)\.|\.(?!\d)|[!?])+", summary or "")
        if seg and seg.strip()
    ])
    word_count = len(summary.split())
    return 2 <= sentence_count <= 3 and 20 <= word_count <= 160


def _summary_covers_requirements(summary: str, facts: dict) -> bool:
    goal_ok, stack_ok, contribution_ok = _summary_requirement_checks(summary, facts)
    return goal_ok and stack_ok and contribution_ok


def _summary_requirement_checks(summary: str, facts: dict) -> tuple[bool, bool, bool]:
    lowered = str(summary or "").lower()

    goal_terms = [str(x).lower() for x in facts.get("goal_terms", []) if str(x).strip()]
    goal_ok = (not goal_terms) or _goal_anchor_matches(summary, goal_terms)

    stack_terms = [
        str(x).lower()
        for x in facts.get("frameworks", []) + facts.get("languages", []) + facts.get("stack_hints", [])
        if str(x).strip()
    ]
    stack_ok = (not stack_terms) or any(term in lowered for term in stack_terms)

    contribution_terms = _contribution_anchor_terms(facts)
    if not _has_strong_contribution_signals(facts):
        contribution_ok = True
    else:
        has_anchor = (not contribution_terms) or any(term in lowered for term in contribution_terms)
        contribution_ok = has_anchor or _has_generic_contribution_phrase(summary)

    return goal_ok, stack_ok, contribution_ok


def _has_generic_contribution_phrase(summary: str) -> bool:
    text = str(summary or "").lower()
    if not text:
        return False
    contribution_verbs = ("contributed", "contribution", "worked on", "focused on", "implemented", "built")
    contribution_domains = ("code", "coding", "documentation", "docs", "testing", "test",
                            "development", "implementation", "delivery")
    return any(t in text for t in contribution_verbs) and any(t in text for t in contribution_domains)


def _goal_anchor_matches(summary: str, goal_terms: list[str]) -> bool:
    lowered = str(summary or "").lower()
    summary_tokens = _token_set(summary)
    if not summary_tokens:
        return False

    low_signal = {
        "project", "goal", "goals", "outcome", "outcomes", "feature", "features",
        "app", "apps", "application", "applications", "workflow", "workflows",
        "service", "services", "system", "systems", "product", "products",
    }

    for raw_term in goal_terms:
        term = str(raw_term).strip().lower()
        if not term:
            continue
        if term in lowered:
            return True
        raw_tokens = _token_set(term)
        if not raw_tokens:
            continue
        informative = {t for t in raw_tokens if len(t) >= 4 and t not in low_signal} or raw_tokens
        overlap = informative & summary_tokens
        if not overlap:
            continue
        if len(overlap) / len(informative) >= 0.5:
            return True
        if len(informative) >= 3 and len(overlap) >= 2:
            return True
        if len(informative) == 1:
            return True

    return False


def _contribution_anchor_terms(facts: dict) -> list[str]:
    stopwords = {
        "and", "the", "with", "for", "from", "into", "onto", "across",
        "this", "that", "was", "were", "have", "has", "had", "project",
        "delivery", "work", "changes",
    }
    terms: list[str] = []

    role = facts.get("role")
    if role:
        terms.extend([t for t in str(role).replace("_", " ").lower().split()
                      if len(t) >= 4 and t not in stopwords])

    commit_focus = facts.get("commit_focus")
    if commit_focus:
        terms.extend([t for t in str(commit_focus).replace("_", " ").lower().split()
                      if len(t) >= 4 and t not in stopwords])

    role_description = facts.get("role_description")
    if role_description:
        terms.extend([t for t in _token_set(str(role_description))
                      if len(t) >= 4 and t not in stopwords])

    commit_pct = facts.get("commit_pct")
    if isinstance(commit_pct, (int, float)):
        terms.append(f"{int(round(float(commit_pct)))}%")

    line_pct = facts.get("line_pct")
    if isinstance(line_pct, (int, float)):
        terms.append(f"{int(round(float(line_pct)))}%")

    for domain, _ in facts.get("activity_breakdown", [])[:2]:
        if domain:
            terms.extend([t for t in str(domain).lower().split()
                          if len(t) >= 4 and t not in stopwords])

    return [t for t in terms if t]


def _has_strong_contribution_signals(facts: dict) -> bool:
    if facts.get("role_description") or facts.get("role") or facts.get("commit_focus"):
        return True
    if isinstance(facts.get("commit_pct"), (int, float)) or isinstance(facts.get("line_pct"), (int, float)):
        return True
    activity = facts.get("activity_breakdown", []) or []
    return bool(activity) and not _is_docs_only_activity(activity)


def _is_docs_only_activity(activity_breakdown: list[tuple[str, float]]) -> bool:
    doc_tokens = {"documentation", "docs", "readme", "doc"}
    non_doc_pct = 0.0
    for domain, pct in activity_breakdown:
        if not (_token_set(str(domain)) & doc_tokens):
            try:
                non_doc_pct += float(pct)
            except (TypeError, ValueError):
                pass
    return non_doc_pct <= 20.0


def _compose_contribution_sentence(
    role: str | None,
    commit_focus: str | None,
    commit_pct: float | None,
    line_pct: float | None,
    activity_breakdown: list[tuple[str, float]] | None,
    allow_percentages: bool = False,
) -> str:
    lead = "I contributed"
    role_text = str(role).replace("_", " ").strip() if role else None
    if role_text:
        lead += f" as a {role_text}"

    detail_phrases: list[str] = []
    if allow_percentages and isinstance(commit_pct, (int, float)):
        detail_phrases.append(f"authoring about {commit_pct:.0f}% of commits")
    elif allow_percentages and isinstance(line_pct, (int, float)):
        detail_phrases.append(f"accounting for about {line_pct:.0f}% of authored lines")

    if commit_focus:
        detail_phrases.append(f"focusing on {str(commit_focus).replace('_', ' ').strip().lower()} changes")

    activity_phrase = _activity_phrase(activity_breakdown or [], allow_percentages=allow_percentages)
    if activity_phrase:
        detail_phrases.append(activity_phrase)

    if detail_phrases:
        return f"{lead}, {join_english(detail_phrases)}."
    return f"{lead} across project delivery tasks."


def _activity_phrase(activity_breakdown: list[tuple[str, float]], *, allow_percentages: bool = False) -> str | None:
    if not activity_breakdown:
        return None
    top = activity_breakdown[:2]
    if not allow_percentages:
        if len(top) == 1:
            return f"primarily through {top[0][0]} work"
        return f"primarily through {top[0][0]} and {top[1][0]} work"
    if len(top) == 1:
        return f"primarily through {top[0][0]} work ({top[0][1]:.0f}%)"
    return f"primarily through {top[0][0]} ({top[0][1]:.0f}%) and {top[1][0]} ({top[1][1]:.0f}%) work"


def _token_set(text: str | None) -> set[str]:
    source = str(text or "")
    return {_normalize_token(t) for t in re.findall(r"[a-z0-9]+", source.lower()) if _normalize_token(t)}


def _normalize_token(token: str) -> str:
    cleaned = "".join(ch for ch in token.lower() if ch.isalnum())
    if not cleaned:
        return ""
    if cleaned.endswith("ies") and len(cleaned) > 4:
        return cleaned[:-3] + "y"
    if cleaned.endswith("es") and len(cleaned) > 4:
        return cleaned[:-2]
    if cleaned.endswith("s") and len(cleaned) > 3:
        return cleaned[:-1]
    return cleaned


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
