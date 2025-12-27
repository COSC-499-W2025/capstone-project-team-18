"""
Tests for functions in `src/database/utils/database_access.py`.

Focus:
- get_project_from_project_name
- get_file_reports (indirect + direct error cases)
"""

import pytest
import datetime

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

from src.database.db import Base, ProjectReportTable, FileReportTable
from src.database.utils.database_access import get_project_from_project_name, get_user_report, _project_report_from_row
from src.database.utils.database_modify import rename_user_report, create_row
from src.classes.statistic import (
    FileStatCollection,
    ProjectStatCollection,
    CodingLanguage,
)
from src.classes.report import ProjectReport
from src.classes.statistic import FileStatCollection, ProjectStatCollection


def test_get_project_from_project_name_success(temp_db):
    '''
    Validate that given an existing project name, a `ProjectReport`
    object is correctly returned.
    '''
    name = 'Project2'
    pr = get_project_from_project_name(name, temp_db)

    assert pr.project_name == name
    assert len(pr.file_reports) == 2

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
    proj_row = create_row(project_report)
    with Session(temp_db) as session:
        session.add(proj_row)
        session.commit()
    with pytest.raises(ValueError):
        get_project_from_project_name(project_report.project_name, temp_db)


def test_get_project_with_multiple_results(temp_db, fr1, fr2):
    project_report = ProjectReport([fr1])
    project_report.project_name = 'fileReport'

    project_report2 = ProjectReport([fr2])
    project_report2.project_name = 'fileReport'

    proj_row = create_row(project_report)
    proj_row2 = create_row(project_report2)

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
        assert pr.project_name == "Project1" or pr.project_name == "Project2"


def test_rename_user_report_success(temp_db):
    ok, msg = rename_user_report(
        "test_user_report", "renamed_portfolio", temp_db)
    assert ok is True
    assert "renamed_portfolio" in msg

    renamed = get_user_report("renamed_portfolio", temp_db)
    assert renamed.report_name == "renamed_portfolio"


def test_rename_user_report_conflict(temp_db):
    from src.database.db import UserReportTable

    with Session(temp_db) as session:
        session.add(UserReportTable(title="existing_portfolio"))
        session.commit()

    ok, msg = rename_user_report(
        "test_user_report", "existing_portfolio", temp_db)
    assert ok is False
    assert "already exists" in msg


def test_rename_user_report_handles_duplicates(temp_db):
    from src.database.db import UserReportTable

    with Session(temp_db) as session:
        duplicate = UserReportTable(title="test_user_report")
        session.add(duplicate)
        session.commit()
        duplicate_id = duplicate.id

    ok, msg = rename_user_report(
        "test_user_report", "renamed_portfolio_dupe", temp_db)
    assert ok is True
    assert "renamed_portfolio_dupe" in msg

    with Session(temp_db) as session:
        renamed = session.get(UserReportTable, duplicate_id)
        assert renamed is not None
        assert renamed.title == "renamed_portfolio_dupe"

        originals = session.execute(
            select(UserReportTable).where(
                UserReportTable.title == "test_user_report")
        ).scalars().all()
        assert len(originals) == 1  # original remains


def test_project_report_from_row_rebuilds_coding_language_ratio(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        proj = ProjectReportTable(
            project_name="proj",
            coding_language_ratio={
                CodingLanguage.PYTHON: 0.6, CodingLanguage.JAVA: 0.4}
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
