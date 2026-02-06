from src.core.report import UserReport
from src.core.portfolio.builder.concrete_builders import ProjectSummariesSectionBuilder
from src.core.statistic import (
    Statistic,
    ProjectStatCollection,
    WeightedSkills,
    CodingLanguage,
)


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
    assert "goals centered on analytics and reporting" in line.lower()
    assert "React and FastAPI" in line
    assert "Python and JavaScript" in line
    assert "about 42% of commits" in line
    assert "feature changes" in line

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
