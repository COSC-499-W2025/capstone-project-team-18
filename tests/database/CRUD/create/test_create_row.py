"""
Tests the create_row() function
"""

from src.database.db import (
    FileReportTable,
    ProjectReportTable,
    UserReportTable,
)
from src.database.utils.database_modify import create_row
from src.classes.report import ProjectReport, UserReport
from src.classes.statistic import FileStatCollection, ProjectStatCollection, UserStatCollection


def test_create_row(fr1, fr2, fr3, fr4):
    '''
    Test that the `create_row()` function in `/src/database/utils/database_modify.py`
    properly returns a new row for a given report object.
    '''
    # Check that a row is properly created from a FileReport
    row = create_row(fr1)

    assert type(row) == FileReportTable
    assert row.filepath == "file1.py"
    assert row.date_created == fr1.get_value(  # type: ignore
        FileStatCollection.DATE_CREATED.value)

    # Check that a row is properly created from a ProjectReport
    project_report = ProjectReport(file_reports=[fr1, fr2])
    proj_row = create_row(project_report)

    assert type(proj_row) == ProjectReportTable
    assert proj_row.project_start_date == project_report.get_value(  # type: ignore
        ProjectStatCollection.PROJECT_START_DATE.value)
    assert proj_row.project_name == "Unknown Project"

    # Check that a row is properly created from a UserReport
    project_report_2 = ProjectReport(file_reports=[fr3, fr4])
    user_report = UserReport(
        project_reports=[project_report, project_report_2], report_name="user_report_test")
    user_row = create_row(user_report)

    assert type(user_row) == UserReportTable
    assert user_row.user_start_date == user_report.get_value(  # type: ignore
        UserStatCollection.USER_START_DATE.value)
