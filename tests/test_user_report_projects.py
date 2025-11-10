from types import SimpleNamespace
from datetime import datetime
import pytest

from classes.report import UserReport  

class _PRStub:
    """Minimal ProjectReport-like stub used in tests."""
    def __init__(self, name, start=None, end=None):
        self.project_name = name
        self._start = start
        self._end = end

    def get_value(self, key):
        if key == "start":
            return self._start
        if key == "end":
            return self._end
        return None


@pytest.fixture(autouse=True)
def patch_project_stat_collection(monkeypatch):
    """
    Replace ProjectStatCollection in the reports module with a simple namespace
    where .PROJECT_START_DATE.value == "start" and .PROJECT_END_DATE.value == "end".
    """
    simple = SimpleNamespace(
        PROJECT_START_DATE=SimpleNamespace(value="start"),
        PROJECT_END_DATE=SimpleNamespace(value="end"),
    )
    import classes.report as _r
    monkeypatch.setattr(_r, "ProjectStatCollection", simple)
    yield


def make_date(y, m, d):
    return datetime(y, m, d)


def test_empty_project_reports_returns_empty_string_and_list():
    ur = UserReport.__new__(UserReport)
    ur.project_reports = []

    assert ur.get_chronological_projects(as_string=True) == ""
    assert ur.get_chronological_projects(as_string=False) == []


def test_always_numbered_and_end_dates_string_exact_output():
    # sample projects 
    p1 = _PRStub("Portfolio Website", start=make_date(2023, 1, 12), end=make_date(2023, 3, 1))
    p2 = _PRStub("Artifact Miner (Capstone Project)", start=make_date(2024, 9, 5), end=make_date(2024, 11, 20))
    p3 = _PRStub("Expense Tracker App", start=make_date(2024, 11, 2), end=None)

    ur = UserReport.__new__(UserReport)
    ur.project_reports = [p2, p3, p1]

    out = ur.get_chronological_projects(as_string=True, include_end_date=False, newest_first=False, numbered=False)
    expected = (
        "1. Portfolio Website - Started Jan 12, 2023 (Ended Mar 01, 2023)\n"
        "2. Artifact Miner (Capstone Project) - Started Sep 05, 2024 (Ended Nov 20, 2024)\n"
        "3. Expense Tracker App - Started Nov 02, 2024 (End date unknown)"
    )
    assert out == expected

def test_always_numbered_and_end_dates_list_and_formatting():
    p1 = _PRStub("A", start=make_date(2021, 6, 1), end=make_date(2021, 9, 1))
    p2 = _PRStub("B", start=make_date(2022, 1, 2), end=None)

    ur = UserReport.__new__(UserReport)
    ur.project_reports = [p1, p2]

    lst = ur.get_chronological_projects(as_string=False)
    # Should be a list and numbered entries must exist and include "(Ended" or "(End date unknown)"
    assert isinstance(lst, list)
    assert lst[0].startswith("1. A - Started")
    assert "(Ended" in lst[0] or "(End date unknown)" in lst[0]
    assert lst[1].startswith("2. B - Started")

def test_newest_first_sorting_and_missing_start_date_last():
    p_old = _PRStub("OldProject", start=make_date(2020, 1, 1), end=None)
    p_new = _PRStub("NewProject", start=make_date(2023, 5, 3), end=None)
    p_unknown = _PRStub("NoStart", start=None, end=None)

    ur = UserReport.__new__(UserReport)
    ur.project_reports = [p_old, p_unknown, p_new]

    # newest_first = True should place NewProject first
    s = ur.get_chronological_projects(as_string=False, newest_first=True)
    assert isinstance(s, list)
    # first entry must be NewProject (numbered "1. NewProject - Started ...")
    assert s[0].startswith("1. NewProject - Started")
    # ensure NoStart (None start_date) goes last (numbered as last index)
    assert s[-1].startswith(f"{len(s)}. NoStart")