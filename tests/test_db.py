'''
This file tests our SQLAlchemy database setup and relationships using a
temporary SQLite database fixture.
'''
from pathlib import Path
import datetime
from datetime import timedelta
import random

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


from database.db import (
    Base,
    FileReportTable,
    ProjectReportTable,
    UserReportTable,
    init_db
)
from src.classes.statistic import StatisticIndex, Statistic, FileStatCollection, ProjectStatCollection, UserStatCollection
from src.classes.report import FileReport, ProjectReport, UserReport


def create_file_report(filename: str):
    '''
    Return a `FileReport` object with random values for the following:
    - number of lines (between 100-250)
    - creation date
    - modified date
    - accessed date
    - file size (between 100-1200)

    The function accepts `filename` as a parameter to help us make sure
    that the names are unique.
    '''

    lines_in_file = int(random.randint(100, 250))

    random_create = datetime.datetime.now() + timedelta(hours=random.randint(1, 10))
    random_access = datetime.datetime.now() + timedelta(
        minutes=random.randint(1, 40), hours=random.randint(1, 5)
    )
    random_modified = datetime.datetime.now() + timedelta(
        minutes=random.randint(1, 30), hours=random.randint(1, 3)
    )
    random_filesize = int(random.randint(100, 1200))

    statistics = StatisticIndex([
        Statistic(FileStatCollection.LINES_IN_FILE.value, lines_in_file),
        Statistic(FileStatCollection.DATE_CREATED.value, random_create),
        Statistic(FileStatCollection.DATE_MODIFIED.value, random_modified),
        Statistic(FileStatCollection.FILE_SIZE_BYTES.value, random_filesize),
    ])

    fr = FileReport(statistics, filename)
    return fr


def create_project_report(fr1: FileReport, fr2: FileReport, collaborative: bool):
    '''
    Given two `FileReport` objects, return a `ProjectReport` object, with an
    additional `IS_GROUP_PROJECT` statistic.
    '''

    # create project report with given file reports
    pr = ProjectReport(file_reports=[fr1, fr2])

    # add collaboration statistic since this isn't automatically done in report.py yet
    pr.add_statistic(
        Statistic(ProjectStatCollection.IS_GROUP_PROJECT.value, collaborative)
    )

    return pr


def create_user_report(pr1: ProjectReport, pr2: ProjectReport | None):
    '''
    Given one or two `ProjectReport` objects, return a `UserReport` object.

    This function is not yet implemented nor used since there is no logic for
    creating user reports in `statistic.py`.
    '''
    if pr2 is not None:
        return UserReport(project_reports=[pr1, pr2])
    else:
        return UserReport(project_reports=[pr1])


def get_row(report: FileReport | ProjectReport | UserReport):
    '''
    Given a `FileReport`, `ProjectReport`, or `UserReport` object,
    create a `FileReportTable`, `ProjectReportTable`, or `UserReportTable`
    with the object's statistics.
    '''
    if type(report) == FileReport:
        new_row = FileReportTable(
            lines_in_file=report.get_value(
                FileStatCollection.LINES_IN_FILE.value),
            date_created=report.get_value(
                FileStatCollection.DATE_CREATED.value),
            date_modified=report.get_value(
                FileStatCollection.DATE_MODIFIED.value),
            file_size_bytes=report.get_value(
                FileStatCollection.FILE_SIZE_BYTES.value),
        )
    elif type(report) == ProjectReport:
        new_row = ProjectReportTable(
            project_start_date=report.get_value(
                ProjectStatCollection.PROJECT_START_DATE.value),
            project_end_date=report.get_value(
                ProjectStatCollection.PROJECT_END_DATE.value),
            is_group_project=report.get_value(
                ProjectStatCollection.IS_GROUP_PROJECT.value),
        )
        '''
        # To establish FK in file reports
        for file_report in report.file_reports:
            row = get_row(file_report)
            new_row.file_reports.append(row)
        '''

    else:
        # TODO: Implement once we have logic for user report generation
        return

    return new_row


@pytest.fixture
def temp_db(tmp_path: Path):
    '''
    Create a temp DB with tables and data.
    Yields the engine for use in tests.
    '''
    db_path = tmp_path / "temp_db.db"
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)  # add columns to temp DB

    # Create fake file reports
    fr1 = create_file_report("file1.py")
    fr2 = create_file_report("file2.py")
    fr3 = create_file_report("file3.py")
    fr4 = create_file_report("file4.py")

    # Create fake project reports
    pr1 = create_project_report(fr2, fr3, False)
    pr2 = create_project_report(fr4, fr1, True)

    # Get rows for the file reports
    stmt1 = get_row(fr1)
    stmt2 = get_row(fr2)
    stmt3 = get_row(fr3)
    stmt4 = get_row(fr4)

    # Get rows for project reports
    stmt6 = get_row(pr1)
    stmt6.file_reports.append(stmt2)  # type: ignore
    stmt6.file_reports.append(stmt3)  # type: ignore

    stmt7 = get_row(pr2)
    stmt7.file_reports.append(stmt4)  # type: ignore
    stmt7.file_reports.append(stmt1)  # type: ignore

    with Session(engine) as session:

        # add file report & project report rows to the DB
        session.add_all([stmt6, stmt7])

        session.commit()  # write the rows to the DB
    try:
        yield engine
    finally:
        # Clean up
        Base.metadata.drop_all(engine)
        engine.dispose()


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
