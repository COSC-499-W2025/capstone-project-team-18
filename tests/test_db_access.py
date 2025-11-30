"""
Tests for functions in `src/database/utils/database_access.py`.

Focus:
- get_project_from_project_name
- get_file_reports (indirect + direct error cases)
"""

import pytest
import datetime
from datetime import timedelta
import random

from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

from src.database.db import Base, ProjectReportTable, FileReportTable, UserReportTable
from src.database.utils.database_access import get_project_from_project_name, get_user_report, _project_report_from_row
from src.database.utils.database_modify import rename_user_report
from src.classes.statistic import (
    FileStatCollection,
    ProjectStatCollection,
    FileDomain,
    CodingLanguage,
)
from src.classes.report import FileReport, ProjectReport, UserReport
from src.classes.statistic import StatisticIndex, Statistic, FileStatCollection, ProjectStatCollection, UserStatCollection


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


def create_user_report(pr1: ProjectReport, pr2: ProjectReport | None, name: str):
    '''
    Given one or two `ProjectReport` objects, return a `UserReport` object.

    This function is not yet implemented nor used since there is no logic for
    creating user reports in `statistic.py`.
    '''
    if pr2 is not None:
        return UserReport(project_reports=[pr1, pr2], report_name=name)
    else:
        return UserReport(project_reports=[pr1], report_name=name)


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
            project_name=report.project_name
        )
        '''
        # To establish FK in file reports
        for file_report in report.file_reports:
            row = get_row(file_report)
            new_row.file_reports.append(row)
        '''

    else:
        new_row = UserReportTable(
            title=report.report_name,  # type: ignore
            user_start_date=report.get_value(
                UserStatCollection.USER_START_DATE.value),
            user_end_date=report.get_value(
                UserStatCollection.USER_END_DATE.value),
        )

    return new_row


@pytest.fixture
def temp_db(tmp_path: Path):
    '''
    Create a temp DB with tables and data.
    Yields the engine for use in tests.
    '''
    db_path = tmp_path / "temp_db.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)  # add columns to temp DB

    # Create fake file reports
    fr1 = create_file_report("file1.py")
    fr2 = create_file_report("file2.py")
    fr3 = create_file_report("file3.py")
    fr4 = create_file_report("file4.py")

    # Create fake project reports
    pr1 = create_project_report(fr2, fr3, False)
    pr1.project_name = 'Project1'
    pr2 = create_project_report(fr4, fr1, True)
    pr2.project_name = 'Project2'

    ur1 = create_user_report(pr1, pr2, 'test_user_report')

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

    # Get a user report row
    stmt8 = get_row(ur1)
    stmt8.project_reports.append(stmt6)  # type: ignore
    stmt8.project_reports.append(stmt7)  # type: ignore

    with Session(engine) as session:

        # add file report & project report rows to the DB
        session.add_all([stmt8])

        session.commit()  # write the rows to the DB
    try:
        yield engine
    finally:
        # Clean up
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_get_project_from_project_name_success(temp_db):
    '''
    Validate that given an existing project name, a `ProjectReport`
    object is correctly returned.
    '''
    name = 'Project2'
    pr = get_project_from_project_name(name, temp_db)

    assert pr.project_name == name
    assert len(pr.file_reports) == 2

    assert pr.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value) is True

    for fr in pr.file_reports:
        assert fr.get_value(
            FileStatCollection.FILE_SIZE_BYTES.value) is not None
        assert fr.get_value(FileStatCollection.DATE_CREATED.value) is not None
        assert fr.get_value(FileStatCollection.DATE_MODIFIED.value) is not None
        assert fr.get_value(FileStatCollection.LINES_IN_FILE.value) is not None


def test_get_project_with_invalid_name(temp_db):
    with pytest.raises(NoResultFound):
        get_project_from_project_name("does-not-exist", temp_db)


def test_get_project_without_file_reports(temp_db):
    project_report = ProjectReport(file_reports=None)
    project_report.project_name = 'noFileReports'
    proj_row = get_row(project_report)
    with Session(temp_db) as session:
        session.add(proj_row)
        session.commit()
    with pytest.raises(ValueError):
        get_project_from_project_name(project_report.project_name, temp_db)


def test_get_project_with_multiple_results(temp_db):
    file_report = create_file_report("testReport.py")
    file_report2 = create_file_report("testReport2.py")
    project_report = ProjectReport([file_report])
    project_report.project_name = 'fileReport'

    project_report2 = ProjectReport([file_report2])
    project_report2.project_name = 'fileReport'

    proj_row = get_row(project_report)
    proj_row2 = get_row(project_report2)

    with Session(temp_db) as session:
        session.add_all([proj_row, proj_row2])
        session.commit()
    with pytest.raises(MultipleResultsFound):
        get_project_from_project_name('fileReport', temp_db)


def test_get_user_from_name_success(temp_db):
    '''
    Validate that given an existing user report
    name, a `UserReport` object is correctly returned.
    '''
    name = 'test_user_report'
    ur = get_user_report(name, temp_db)

    assert ur.report_name == name
    assert len(ur.project_reports) == 2

    for pr in ur.project_reports:
        assert pr.get_value(
            ProjectStatCollection.IS_GROUP_PROJECT.value) is not None
        assert pr.project_name == "Project1" or pr.project_name == "Project2"


def test_rename_user_report_success(temp_db):
    ok, msg = rename_user_report("test_user_report", "renamed_portfolio", temp_db)
    assert ok is True
    assert "renamed_portfolio" in msg

    renamed = get_user_report("renamed_portfolio", temp_db)
    assert renamed.report_name == "renamed_portfolio"


def test_rename_user_report_conflict(temp_db):
    from src.database.db import UserReportTable

    with Session(temp_db) as session:
        session.add(UserReportTable(title="existing_portfolio"))
        session.commit()

    ok, msg = rename_user_report("test_user_report", "existing_portfolio", temp_db)
    assert ok is False
    assert "already exists" in msg


def test_project_report_from_row_rebuilds_coding_language_ratio(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        proj = ProjectReportTable(
            project_name="proj",
            coding_language_ratio={"Python": 0.6, "Java": 0.4}
        )
        file_row = FileReportTable(
            filepath="a.py",
            lines_in_file=1,
            date_created=datetime.datetime.now(),
            date_modified=datetime.datetime.now(),
            file_size_bytes=1
        )
        proj.file_reports.append(file_row)  # type: ignore
        session.add(proj)
        session.commit()

        row = session.execute(select(ProjectReportTable)).scalar_one()
        pr = _project_report_from_row(row, engine)
        ratio = pr.get_value(ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

        assert ratio.get(CodingLanguage.PYTHON) == 0.6
        assert ratio.get(CodingLanguage.JAVA) == 0.4
