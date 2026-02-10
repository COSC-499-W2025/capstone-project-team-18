"""
Tests CRUD for the ProjectReport object
"""

from sqlmodel import Session
from src.database.api.CRUD.projects import get_project_report_by_name
from src.core.statistic import FileStatCollection
from src.core.statistic.statistic_models import FileDomain


def test_get_existing_project(temp_db):
    """
    Temp DB should have project reports, lets try to get them back
    """
    with Session(temp_db) as session:
        project = get_project_report_by_name(session, "Project1")
        assert project is not None
        assert project.project_name == "Project1"
        assert len(project.file_reports) == 2
        file_names = {fr.filepath for fr in project.file_reports}
        assert file_names == {"file2.py", "file3.py"}

        for fr in project.file_reports:
            assert fr.get_value(
                FileStatCollection.FILE_SIZE_BYTES.value) is not None
            assert fr.get_value(
                FileStatCollection.DATE_CREATED.value) is not None
            assert fr.get_value(
                FileStatCollection.DATE_MODIFIED.value) is not None
            assert fr.get_value(
                FileStatCollection.LINES_IN_FILE.value) is not None
            assert fr.get_value(
                FileStatCollection.TYPE_OF_FILE.value) is FileDomain.CODE


def test_get_nonexistent_project_returns_none(temp_db):
    with Session(temp_db) as session:
        project = get_project_report_by_name(session, "NonexistentProject")
        assert project is None
