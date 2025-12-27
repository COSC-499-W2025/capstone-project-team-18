'''
This file tests our SQLAlchemy database setup and relationships using a
temporary SQLite database fixture.
'''

from sqlalchemy import inspect
from sqlalchemy.orm import Session


from src.database.db import (
    FileReportTable,
    ProjectReportTable,
    UserReportTable,
)
from src.database.utils.database_modify import create_row
from src.classes.report import ProjectReport, UserReport
from src.classes.statistic import FileStatCollection, ProjectStatCollection, UserStatCollection


def test_tables_exist(temp_db):
    inspector = inspect(temp_db)
    tables = set(inspector.get_table_names())
    assert {"file_report", "project_report",
            "user_report", "association_table"} <= tables


def test_sample_data_inserted(temp_db):
    # check that data was actually put into the DB
    with Session(temp_db) as session:
        file_count = session.query(FileReportTable).count()
        project_count = session.query(ProjectReportTable).count()
        # user_count = session.query(UserReportTable).count()

        assert file_count == 4  # 4 file reports
        assert project_count == 2  # 2 project reports
        # assert user_count == 1  # 1 user report


def test_file_to_project_relationship(temp_db):
    '''
    Check that one-to-many relationship of ProjectReport -> FileReports
    is configured properly
    '''
    with Session(temp_db) as session:
        # check that pr1 is in DB
        project = session.query(ProjectReportTable).first()
        assert project is not None

        # check that there are 2 file reports associated with pr1
        assert len(project.file_reports) == 2

        # child rows should reference parent PK via FK
        for fr in project.file_reports:
            assert fr.project_id == project.id


"""
def test_project_to_user_many_to_many(temp_db):
    '''
    Check that bi-directional many-to-many relationship of
    UserReport <-> ProjectReport is configured properly
    '''
    with Session(temp_db) as session:
        user = session.query(UserReportTable).first()
        assert user is not None
        assert len(user.project_reports) == 2

        # Back-populates should work in the other direction too
        for p in user.project_reports:
            assert user in p.user_reports
"""


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
