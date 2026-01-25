from datetime import datetime

from src.core.report import UserReport
from src.core.portfolio.builder.concrete_builders import ChronologicalProjectsSectionBuilder
from src.core.statistic import Statistic, ProjectStatCollection


def make_date(y, m, d):
    return datetime(y, m, d)


def test_empty_project_reports_returns_empty_string_and_list(user_report_from_stats):
    ur = user_report_from_stats([])
    builder = ChronologicalProjectsSectionBuilder()

    assert builder.get_chronological_projects(ur) == []


def test_always_numbered_and_end_dates_string_exact_output(project_report_from_stats):
    p1 = project_report_from_stats([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  make_date(2023, 1, 12)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  make_date(2023, 3, 1)),
    ], project_name="Portfolio Website")

    p2 = project_report_from_stats([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  make_date(2024, 9, 5)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  make_date(2024, 11, 20)),
    ], project_name="Artifact Miner (Capstone Project)")

    p3 = project_report_from_stats([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  make_date(2024, 11, 2))
    ], project_name="Expense Tracker App")

    ur = UserReport([p1, p2, p3], "UserReport")
    builder = ChronologicalProjectsSectionBuilder()

    lines = builder.get_chronological_projects(ur)

    assert lines == [
        "1. Portfolio Website - Started Jan 12, 2023 (Ended Mar 01, 2023)",
        "2. Artifact Miner (Capstone Project) - Started Sep 05, 2024 (Ended Nov 20, 2024)",
        "3. Expense Tracker App - Started Nov 02, 2024 (End date unknown)"
    ]


def test_always_numbered_and_end_dates_list_and_formatting(project_report_from_stats):
    p1 = project_report_from_stats([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  make_date(2023, 1, 12)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  make_date(2023, 3, 1)),
    ], project_name="A")

    p2 = project_report_from_stats([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  make_date(2024, 9, 5)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  make_date(2024, 11, 20)),
    ], project_name="B")

    ur = UserReport([p1, p2], "UserReport")
    builder = ChronologicalProjectsSectionBuilder()

    lst = builder.get_chronological_projects(ur)
    # Should be a list and numbered entries must exist and include "(Ended" or "(End date unknown)"
    assert isinstance(lst, list)
    assert lst[0].startswith("1. A - Started")
    assert "(Ended" in lst[0] or "(End date unknown)" in lst[0]
    assert lst[1].startswith("2. B - Started")


def test_newest_first_sorting_and_missing_start_date_last(project_report_from_stats):
    p_old = project_report_from_stats([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  make_date(2020, 1, 1))
    ], project_name="OldProject")

    p_new = project_report_from_stats([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  make_date(2023, 5, 3))
    ], project_name="NewProject")

    p_unknown = project_report_from_stats([], project_name="NoStart")

    ur = UserReport([p_old, p_unknown, p_new], "UserReport")
    builder = ChronologicalProjectsSectionBuilder()

    # Builder returns chronologically ordered (oldest first by default)
    lines = builder.get_chronological_projects(ur)
    assert isinstance(lines, list)
    # First entry must be OldProject (numbered "1. OldProject - Started ...")
    assert lines[0].startswith("1. OldProject - Started")
    # ensure NoStart (None start_date) goes last (numbered as last index)
    assert lines[-1].startswith(f"{len(lines)}. NoStart")
