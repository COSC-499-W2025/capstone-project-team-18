from datetime import datetime

from src.core.report import UserReport, ProjectReport
from src.core.portfolio.builder.concrete_builders import UserSkillsSectionBuilder
from src.core.statistic import (
    StatisticIndex,
    Statistic,
    ProjectStatCollection,
    WeightedSkills,
)


def make_project(start_date: datetime | None, skill_names: list[str], project_report_from_stats=None) -> ProjectReport:
    """
    Helper to build a ProjectReport with a PROJECT_START_DATE and
    PROJECT_SKILLS_DEMONSTRATED statistic.

    Accepts the `project_report_from_stats` pytest fixture when provided
    to construct ProjectReport without using .from_statistics.
    """
    stats = []

    if start_date is not None:
        stats.append(
            Statistic(
                ProjectStatCollection.PROJECT_START_DATE.value,
                start_date,
            )
        )

    if skill_names:
        skills = [
            WeightedSkills(skill_name=name, weight=1.0)
            for name in skill_names
        ]
        stats.append(
            Statistic(
                ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
                skills,
            )
        )

    if project_report_from_stats is not None:
        return project_report_from_stats(stats)

    # Fallback for non-pytest usage
    return ProjectReport([], None, None, None, statistics=StatisticIndex(stats))


def test_chronological_skills_basic_ordering(project_report_from_stats):
    """
    Skills should be ordered by the earliest project start date
    in which they appear.
    """
    proj1 = make_project(datetime(2023, 1, 1), [
                         "Python", "React"], project_report_from_stats)
    proj2 = make_project(datetime(2024, 1, 1), [
                         "Docker"], project_report_from_stats)
    proj3 = make_project(datetime(2022, 6, 1), [
                         "Python"], project_report_from_stats)

    user = UserReport([proj1, proj2, proj3], "UserReport1")
    builder = UserSkillsSectionBuilder()

    lines = builder.get_chronological_skills(user)

    assert lines == [
        "Python — First exercised Jun 01, 2022",
        "React — First exercised Jan 01, 2023",
        "Docker — First exercised Jan 01, 2024",
    ]


def test_chronological_skills_newest_first(project_report_from_stats):
    """
    Reversed chronological ordering should show newest skills first.
    """
    proj1 = make_project(datetime(2023, 1, 1), [
                         "Python"], project_report_from_stats)
    proj2 = make_project(datetime(2024, 1, 1), [
                         "React"], project_report_from_stats)

    user = UserReport([proj1, proj2], "UserReport2")
    builder = UserSkillsSectionBuilder()

    lines = builder.get_chronological_skills(user)
    reversed_lines = list(reversed(lines))

    assert reversed_lines == [
        "React — First exercised Jan 01, 2024",
        "Python — First exercised Jan 01, 2023",
    ]


def test_chronological_skills_undated_skills_go_last(project_report_from_stats):
    """
    Skills with no known first date should be listed after dated skills
    and marked as 'unknown date'.
    """
    proj_undated = make_project(None, ["Python"], project_report_from_stats)
    proj_dated = make_project(
        datetime(2024, 1, 1), ["React"], project_report_from_stats)

    user = UserReport([proj_undated, proj_dated], "UserReport3")
    builder = UserSkillsSectionBuilder()

    lines = builder.get_chronological_skills(user)

    assert lines[0] == "React — First exercised Jan 01, 2024"
    assert "Python — First exercised on an unknown date" in lines


def test_chronological_skills_no_projects():
    """
    If there are no projects, an empty list should be returned.
    """
    user = UserReport([], "")
    builder = UserSkillsSectionBuilder()

    assert builder.get_chronological_skills(user) == []


def test_chronological_skills_list_output_format(project_report_from_stats):
    """
    Ensure the builder returns a list of formatted skill strings.
    """
    proj = make_project(datetime(2023, 5, 10), [
                        "Python"], project_report_from_stats)
    user = UserReport([proj], "UserReport4")
    builder = UserSkillsSectionBuilder()

    result = builder.get_chronological_skills(user)

    assert result == ["Python — First exercised May 10, 2023"]
