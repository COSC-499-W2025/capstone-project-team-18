"""
This file has the fixtures and helpers for the database test suite
"""

"""
Tests for functions in `src/database/utils/database_access.py`.

Focus:
- get_project_from_project_name
- get_file_reports (indirect + direct error cases)
"""

from src.core.report import FileReport, ProjectReport
from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path
import datetime
import pytest
from src.core.report import FileReport
from src.core.statistic import StatisticIndex, Statistic, FileStatCollection
from src.database.api.CRUD.projects import save_project_report


@pytest.fixture
def fr1() -> FileReport:
    return FileReport(
        StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 150),
            Statistic(FileStatCollection.DATE_CREATED.value,
                      datetime.datetime(2025, 1, 1, 10, 0)),
            Statistic(FileStatCollection.DATE_MODIFIED.value,
                      datetime.datetime(2025, 1, 2, 12, 0)),
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 500),
        ]),
        "file1.py"
    )


@pytest.fixture
def fr2() -> FileReport:
    return FileReport(
        StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 200),
            Statistic(FileStatCollection.DATE_CREATED.value,
                      datetime.datetime(2025, 2, 1, 10, 0)),
            Statistic(FileStatCollection.DATE_MODIFIED.value,
                      datetime.datetime(2025, 2, 2, 12, 0)),
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 600),
        ]),
        "file2.py"
    )


@pytest.fixture
def fr3() -> FileReport:
    return FileReport(
        StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 180),
            Statistic(FileStatCollection.DATE_CREATED.value,
                      datetime.datetime(2025, 3, 1, 10, 0)),
            Statistic(FileStatCollection.DATE_MODIFIED.value,
                      datetime.datetime(2025, 3, 2, 12, 0)),
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 700),
        ]),
        "file3.py"
    )


@pytest.fixture
def fr4() -> FileReport:
    return FileReport(
        StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 120),
            Statistic(FileStatCollection.DATE_CREATED.value,
                      datetime.datetime(2025, 4, 1, 10, 0)),
            Statistic(FileStatCollection.DATE_MODIFIED.value,
                      datetime.datetime(2025, 4, 2, 12, 0)),
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 550),
        ]),
        "file4.py"
    )


@pytest.fixture
def temp_db(tmp_path: Path, fr1, fr2, fr3, fr4):
    """
    Create a temp DB with tables and deterministic file/project/user reports.
    Yields the engine for use in tests.
    """
    db_path = tmp_path / "temp_db.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)  # add columns to temp DB

    pr1 = ProjectReport(file_reports=[fr2, fr3], project_name="Project1")
    pr2 = ProjectReport(file_reports=[fr4, fr1], project_name="Project2")

    with Session(engine) as session:
        save_project_report(session, pr1, 0)
        save_project_report(session, pr2, 0)

    try:
        yield engine
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
