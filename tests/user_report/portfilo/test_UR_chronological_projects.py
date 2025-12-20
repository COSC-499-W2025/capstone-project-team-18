from datetime import datetime

from src.classes.report import UserReport
from src.classes.statistic import Statistic, ProjectStatCollection


def make_date(y, m, d):
    return datetime(y, m, d)


def test_empty_project_reports_returns_empty_string_and_list(user_report_from_stats):
    ur = user_report_from_stats([])

    assert ur.get_chronological_projects(as_string=True) == ""
    assert ur.get_chronological_projects(as_string=False) == []


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

    out = ur.get_chronological_projects(
        as_string=True, include_end_date=False, newest_first=False, numbered=False)

    expected = (
        "1. Portfolio Website - Started Jan 12, 2023 (Ended Mar 01, 2023)\n"
        "2. Artifact Miner (Capstone Project) - Started Sep 05, 2024 (Ended Nov 20, 2024)\n"
        "3. Expense Tracker App - Started Nov 02, 2024 (End date unknown)"
    )
    assert out == expected


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

    lst = ur.get_chronological_projects(as_string=False)
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

    # newest_first = True should place NewProject first
    s = ur.get_chronological_projects(as_string=False, newest_first=True)
    assert isinstance(s, list)
    # first entry must be NewProject (numbered "1. NewProject - Started ...")
    assert s[0].startswith("1. NewProject - Started")
    # ensure NoStart (None start_date) goes last (numbered as last index)
    assert s[-1].startswith(f"{len(s)}. NoStart")
