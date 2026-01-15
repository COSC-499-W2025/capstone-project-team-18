"""
Tests for retieving project and user reports from the db.
"""

import pytest

from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

from src.database.utils.database_access import get_project_from_project_name, get_user_report
from src.database.utils.database_modify import create_row
from src.classes.statistic import (
    FileStatCollection,
)
from src.classes.report import ProjectReport
from src.classes.statistic import FileStatCollection


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
