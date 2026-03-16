"""
Tests CRUD for the ProjectReport object
"""

import datetime
from sqlmodel import Session
from src.database.api.CRUD.projects import get_project_report_by_name, save_project_report
from src.core.report import FileReport, ProjectReport
from src.core.statistic import FileStatCollection, StatisticIndex, Statistic
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


def _build_file_report(project_name: str, file_name: str) -> FileReport:
    return FileReport(
        StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 10),
            Statistic(FileStatCollection.DATE_CREATED.value,
                      datetime.datetime(2025, 1, 1, 10, 0)),
            Statistic(FileStatCollection.DATE_MODIFIED.value,
                      datetime.datetime(2025, 1, 2, 10, 0)),
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 100),
            Statistic(FileStatCollection.TYPE_OF_FILE.value, FileDomain.CODE)
        ]),
        file_name,
        is_info_file=False,
        file_hash=b"hash",
        project_name=project_name
    )


def test_save_project_report_versions_existing_project(temp_db):
    with Session(temp_db) as session:
        new_report = ProjectReport(
            file_reports=[_build_file_report("Project1", "new_file.py")],
            project_name="Project1"
        )

        saved_model = save_project_report(session, new_report, 0)
        session.commit()

        assert saved_model.project_name == "Project1_2"
        assert saved_model.analyzed_count == 2
        assert saved_model.parent == "Project1"
        assert len(saved_model.file_reports) == 1
        assert saved_model.file_reports[0].project_name == "Project1_2"


def test_save_project_report_versions_chain_parent_points_to_latest(temp_db):
    with Session(temp_db) as session:
        report_v2 = ProjectReport(
            file_reports=[_build_file_report("Project1", "v2.py")],
            project_name="Project1"
        )
        save_project_report(session, report_v2, 0)
        session.commit()

        report_v3 = ProjectReport(
            file_reports=[_build_file_report("Project1", "v3.py")],
            project_name="Project1"
        )
        saved_v3 = save_project_report(session, report_v3, 0)
        session.commit()

        assert saved_v3.project_name == "Project1_3"
        assert saved_v3.analyzed_count == 3
        assert saved_v3.parent == "Project1_2"


def test_save_project_report_new_project_initializes_analysis_fields(temp_db):
    with Session(temp_db) as session:
        new_report = ProjectReport(
            file_reports=[_build_file_report("BrandNewProject", "main.py")],
            project_name="BrandNewProject"
        )

        saved_model = save_project_report(session, new_report, 0)
        session.commit()

        assert saved_model.project_name == "BrandNewProject"
        assert saved_model.analyzed_count == 1
        assert saved_model.parent is None
