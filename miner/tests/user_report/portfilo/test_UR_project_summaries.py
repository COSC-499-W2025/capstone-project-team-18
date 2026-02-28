import pytest

from src.core.ML.models.contribution_analysis import project_summary_generator as psg
from src.core.report import UserReport
from src.core.portfolio.builder.concrete_builders import ProjectSummariesSectionBuilder
from src.core.statistic import (
    Statistic,
    ProjectStatCollection,
    WeightedSkills,
    CodingLanguage,
    FileDomain,
)


@pytest.fixture(autouse=True)
def disable_project_summary_model(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_DISABLE_PROJECT_SUMMARY_MODEL", "1")


def test_project_summaries_empty_user_report_returns_no_lines(user_report_from_stats):
    user_report = user_report_from_stats([])
    builder = ProjectSummariesSectionBuilder()

    assert builder.get_project_summaries(user_report) == []


def test_project_summary_builds_grounded_three_sentence_text(project_report_from_stats):
    project = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.PROJECT_THEMES.value, ["analytics", "reporting"]),
            Statistic(
                ProjectStatCollection.PROJECT_FRAMEWORKS.value,
                [WeightedSkills("React", 0.9), WeightedSkills("FastAPI", 0.8)],
            ),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {CodingLanguage.PYTHON: 0.7, CodingLanguage.JAVASCRIPT: 0.3},
            ),
            Statistic(ProjectStatCollection.COLLABORATION_ROLE.value, "core_contributor"),
            Statistic(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value, 42.0),
            Statistic(
                ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value,
                {"feature": 70.0, "docs": 30.0},
            ),
        ],
        project_name="Insight Portal",
    )

    user_report = UserReport([project], "UserReport")
    builder = ProjectSummariesSectionBuilder()
    lines = builder.get_project_summaries(user_report)

    assert len(lines) == 1
    line = lines[0]
    assert line.startswith("Insight Portal:")
    assert "analytics and reporting" in line.lower()
    assert "React and FastAPI" in line
    assert "written in Python and JavaScript" in line
    assert "about 42% commits" in line
    assert "feature" in line.lower()

    summary_text = line.split(": ", 1)[1]
    assert 2 <= summary_text.count(".") <= 3


def test_project_summary_prefers_role_description_for_contribution(project_report_from_stats):
    project = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.PROJECT_TAGS.value, ["automation", "api"]),
            Statistic(
                ProjectStatCollection.PROJECT_FRAMEWORKS.value,
                [WeightedSkills("FastAPI", 1.0)],
            ),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {CodingLanguage.PYTHON: 1.0},
            ),
            Statistic(
                ProjectStatCollection.ROLE_DESCRIPTION.value,
                "Led backend delivery and coordinated integration testing",
            ),
        ],
        project_name="Ops API",
    )

    user_report = UserReport([project], "UserReport")
    builder = ProjectSummariesSectionBuilder()
    lines = builder.get_project_summaries(user_report)

    assert len(lines) == 1
    assert "Led backend delivery and coordinated integration testing." in lines[0]


def test_to_user_readable_string_includes_project_summaries_section(project_report_from_stats):
    project = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.PROJECT_TAGS.value, ["dashboard", "kpi"]),
            Statistic(
                ProjectStatCollection.PROJECT_FRAMEWORKS.value,
                [WeightedSkills("React", 0.7)],
            ),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {CodingLanguage.TYPESCRIPT: 0.8, CodingLanguage.CSS: 0.2},
            ),
            Statistic(ProjectStatCollection.COLLABORATION_ROLE.value, "leader"),
            Statistic(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value, 55.0),
            Statistic(
                ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value,
                {"feature": 60.0, "bugfix": 40.0},
            ),
        ],
        project_name="KPI Dashboard",
    )

    user_report = UserReport([project], "UserReport")
    readable = user_report.to_user_readable_string()

    assert "## Project Summaries" in readable
    assert "KPI Dashboard:" in readable


def test_project_summary_uses_ml_output_when_available(project_report_from_stats, monkeypatch):
    project = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.PROJECT_THEMES.value, ["analytics"]),
            Statistic(
                ProjectStatCollection.PROJECT_FRAMEWORKS.value,
                [WeightedSkills("React", 0.9)],
            ),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {CodingLanguage.JAVASCRIPT: 1.0},
            ),
            Statistic(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value, 50.0),
        ],
        project_name="ML Portal",
    )
    user_report = UserReport([project], "UserReport")

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_project_summary",
        lambda _facts: (
            "This project targeted analytics workflows for product reporting. "
            "It was implemented with React and JavaScript. "
            "My contribution covered 50% of commits focused on feature delivery."
        ),
    )

    builder = ProjectSummariesSectionBuilder()
    lines = builder.get_project_summaries(user_report)

    assert len(lines) == 1
    assert "This project targeted analytics workflows for product reporting." in lines[0]


def test_project_summary_fallback_uses_activity_breakdown(project_report_from_stats, monkeypatch):
    project = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.PROJECT_THEMES.value, ["reporting"]),
            Statistic(
                ProjectStatCollection.PROJECT_FRAMEWORKS.value,
                [WeightedSkills("FastAPI", 1.0)],
            ),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {CodingLanguage.PYTHON: 1.0},
            ),
            Statistic(
                ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value,
                {
                    FileDomain.CODE: 0.62,
                    FileDomain.DOCUMENTATION: 0.38,
                },
            ),
        ],
        project_name="Activity API",
    )
    user_report = UserReport([project], "UserReport")

    # Force fallback path by returning no ML summary.
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_project_summary",
        lambda _facts: None,
    )

    builder = ProjectSummariesSectionBuilder()
    lines = builder.get_project_summaries(user_report)

    assert len(lines) == 1
    assert "primarily through code (62%) and documentation (38%) work" in lines[0].lower()


def test_project_summary_validator_counts_exclamation_and_question_sentences():
    summary = (
        "The project focused on analytics and reporting outcomes! "
        "It was implemented with FastAPI and Python for service reliability and clear interfaces? "
        "I contributed as a core contributor across feature delivery and system documentation."
    )
    facts = {
        "goal_terms": ["analytics"],
        "frameworks": ["FastAPI"],
        "languages": ["Python"],
        "role": "core_contributor",
        "commit_focus": "feature",
        "activity_breakdown": [],
    }

    ok, reason = psg._is_valid_summary(summary, facts)
    assert ok is True, reason


def test_project_summary_normalizes_ratio_commit_percentage(project_report_from_stats, monkeypatch):
    project = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.PROJECT_THEMES.value, ["analytics"]),
            Statistic(
                ProjectStatCollection.PROJECT_FRAMEWORKS.value,
                [WeightedSkills("FastAPI", 1.0)],
            ),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {CodingLanguage.PYTHON: 1.0},
            ),
            # Ratio format (0-1) should be normalized to percentage (0-100).
            Statistic(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value, 0.42),
            Statistic(
                ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value,
                {"feature": 100.0},
            ),
        ],
        project_name="Ratio API",
    )
    user_report = UserReport([project], "UserReport")

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_project_summary",
        lambda _facts: None,
    )

    builder = ProjectSummariesSectionBuilder()
    lines = builder.get_project_summaries(user_report)

    assert len(lines) == 1
    assert "42% of commits" in lines[0]


def test_project_summary_validator_accepts_pluralized_goal_anchor():
    summary = (
        "The project focused on analytics dashboards for operational reporting. "
        "It was implemented with FastAPI and Python for reliable delivery workflows. "
        "I contributed as a core contributor with emphasis on feature changes."
    )
    facts = {
        "goal_terms": ["dashboard"],
        "frameworks": ["FastAPI"],
        "languages": ["Python"],
        "role": "core_contributor",
        "commit_focus": "feature",
        "activity_breakdown": [],
    }

    ok, reason = psg._is_valid_summary(summary, facts)
    assert ok is True, reason


def test_project_summary_validator_allows_missing_percent_when_textual_contribution_present():
    summary = (
        "The project focused on analytics and reporting outcomes for operational visibility. "
        "It was implemented with FastAPI and Python across API and service workflows. "
        "I contributed as a core contributor focused on feature changes and documentation quality."
    )
    facts = {
        "goal_terms": ["analytics"],
        "frameworks": ["FastAPI"],
        "languages": ["Python"],
        "role": "core_contributor",
        "commit_focus": "feature",
        "commit_pct": 42.0,
        "line_pct": None,
        "activity_breakdown": [("documentation", 38.0)],
    }

    ok, reason = psg._is_valid_summary(summary, facts)
    assert ok is True, reason


def test_project_summary_repair_enforces_canonical_activity_percentages():
    facts = {
        "project_name": "web-analytics-portal",
        "goal_terms": ["Data visualization", "Stakeholder dashboards"],
        "frameworks": ["react"],
        "languages": ["JavaScript", "CSS"],
        "stack_hints": [],
        "role": None,
        "role_description": None,
        "commit_focus": None,
        "commit_pct": None,
        "line_pct": None,
        "activity_breakdown": [("code", 62.0), ("documentation", 38.0)],
        "allow_percentages": True,
    }
    raw = (
        "The project focused on data visualization outcomes. "
        "It was implemented with react and written in JavaScript and CSS. "
        "I contributed across code and documentation changes."
    )

    repaired = psg._repair_summary(raw, facts)

    assert "Contributed through coding 62% and documentation 38%." in repaired


def test_project_summary_repair_skips_percentage_enforcement_when_not_allowed():
    facts = {
        "project_name": "docs-only-project",
        "goal_terms": ["Documentation"],
        "frameworks": [],
        "languages": ["Python"],
        "stack_hints": [],
        "role": None,
        "role_description": None,
        "commit_focus": None,
        "commit_pct": None,
        "line_pct": None,
        "activity_breakdown": [("documentation", 100.0)],
        "allow_percentages": False,
    }
    raw = (
        "The project focused on documentation outcomes. "
        "It was primarily written in Python. "
        "I contributed through documentation work."
    )

    repaired = psg._repair_summary(raw, facts)

    assert "Contributed through" not in repaired
    assert "%" not in repaired


def test_project_summary_normalizer_collapses_decimal_and_rounded_duplicates():
    facts = {
        "activity_breakdown": [("code", 43.0), ("documentation", 39.0), ("testing", 18.0)],
    }
    noisy = (
        "The development process involved 42.86% coding 43%, "
        "39.29% documentation 39%, and 17.86% testing 18%."
    )

    normalized = psg._normalize_contribution_percentage_noise(noisy, facts)

    assert "42.86%" not in normalized
    assert "39.29%" not in normalized
    assert "17.86%" not in normalized
    assert "43% coding" in normalized
    assert "39% documentation" in normalized
    assert "18% testing" in normalized


def test_builder_accepts_generic_contribution_phrase_with_strong_signals():
    builder = ProjectSummariesSectionBuilder()
    facts = {
        "goal_terms": ["analytics"],
        "frameworks": ["FastAPI"],
        "languages": ["Python"],
        "stack_hints": [],
        "role": "core_contributor",
        "commit_focus": "feature",
        "commit_pct": 42.0,
        "line_pct": None,
        "activity_breakdown": [("code", 62.0), ("documentation", 38.0)],
    }
    summary = (
        "The project focused on analytics outcomes. "
        "It was implemented with FastAPI and Python. "
        "Contributed through coding and documentation work."
    )

    goal_ok, stack_ok, contribution_ok = builder._summary_requirement_checks(summary, facts)

    assert goal_ok is True
    assert stack_ok is True
    assert contribution_ok is True
