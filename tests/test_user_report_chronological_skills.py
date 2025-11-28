import pytest
from datetime import date

from src.classes.report import UserReport, ProjectReport
from src.classes.statistic import (
    StatisticIndex,
    Statistic,
    ProjectStatCollection,
    WeightedSkills,
)


def make_project(start_date: date | None, skill_names: list[str]) -> ProjectReport:
    """
    Helper to build a ProjectReport with a PROJECT_START_DATE and
    PROJECT_SKILLS_DEMONSTRATED statistic.
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

    return ProjectReport.from_statistics(StatisticIndex(stats))


def test_chronological_skills_basic_ordering():
    """
    Skills should be ordered by the earliest project start date
    in which they appear.
    """
    proj1 = make_project(date(2023, 1, 1), ["Python", "React"])
    proj2 = make_project(date(2024, 1, 1), ["Docker"])
    proj3 = make_project(date(2022, 6, 1), ["Python"])

    user = UserReport([proj1, proj2, proj3], "UserReport1")

    lines = user.get_chronological_skills(as_string=False)

    assert lines == [
        "Python — First exercised Jun 01, 2022",
        "React — First exercised Jan 01, 2023",
        "Docker — First exercised Jan 01, 2024",
    ]


def test_chronological_skills_newest_first():
    """
    newest_first=True should reverse the chronological ordering.
    """
    proj1 = make_project(date(2023, 1, 1), ["Python"])
    proj2 = make_project(date(2024, 1, 1), ["React"])

    user = UserReport([proj1, proj2], "UserReport2")

    lines = user.get_chronological_skills(as_string=False, newest_first=True)

    assert lines == [
        "React — First exercised Jan 01, 2024",
        "Python — First exercised Jan 01, 2023",
    ]


def test_chronological_skills_undated_skills_go_last():
    """
    Skills with no known first date should be listed after dated skills
    and marked as 'unknown date'.
    """
    proj_undated = make_project(None, ["Python"])
    proj_dated = make_project(date(2024, 1, 1), ["React"])

    user = UserReport([proj_undated, proj_dated], "UserReport3")

    lines = user.get_chronological_skills(as_string=False)

    assert lines[0] == "React — First exercised Jan 01, 2024"
    assert "Python — First exercised on an unknown date" in lines


def test_chronological_skills_no_projects():
    """
    If there are no projects, an empty string or empty list should be returned.
    """
    user = UserReport([], "")

    assert user.get_chronological_skills(as_string=True) == ""
    assert user.get_chronological_skills(as_string=False) == []


def test_chronological_skills_string_output_format():
    """
    Ensure as_string=True returns a newline-separated string.
    """
    proj = make_project(date(2023, 5, 10), ["Python"])
    user = UserReport([proj], "UserReport4")

    result = user.get_chronological_skills(as_string=True)

    assert result == "Python — First exercised May 10, 2023"
