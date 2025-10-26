'''
This file tests our SQLAlchemy database setup and relationships using a
temporary SQLite database fixture.
'''
from pathlib import Path
import datetime
from datetime import timedelta
import random

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from database.db import (
    Base,
    UserPreferencesTable,
    FileReportTable,
    ProjectReportTable,
    UserReportTable,
)


def create_file_report():
    '''
    Add a row to FileReportTable with random dates and filesize.
    '''
    random_create = datetime.datetime.now() + timedelta(hours=random.randint(1, 10))
    random_access = datetime.datetime.now() + timedelta(
        minutes=random.randint(1, 40), hours=random.randint(1, 5)
    )
    random_modified = datetime.datetime.now() + timedelta(
        minutes=random.randint(1, 30), hours=random.randint(1, 3)
    )
    return FileReportTable(
        date_created=random_create,
        date_accessed=random_access,
        date_modified=random_modified,
        filesize=random.randint(100, 1200),
    )


def create_project_report(file_rep_one: FileReportTable, file_rep_two: FileReportTable, collaborative: bool):
    '''
    Add a row to ProjectReportTable using two file reports.
    '''
    start_date = min(file_rep_one.date_created, file_rep_two.date_created)
    end_date = max(file_rep_one.date_modified, file_rep_two.date_modified)
    total_size = (file_rep_one.filesize or 0) + (file_rep_two.filesize or 0)

    pr = ProjectReportTable(
        collaborative=collaborative,
        start_date=start_date,
        end_date=end_date,
        total_size=total_size,
        lines_of_code=random.randint(100, 1200),
    )
    # establish one-to-many relationship with ORM
    pr.file_reports = [file_rep_one, file_rep_two]
    return pr


@pytest.fixture
def temp_db(tmp_path: Path):
    '''
    Create a temp DB with tables and data.
    Yields the engine for use in tests.
    '''
    db_path = tmp_path / "temp_db.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)  # create tables

    with Session(engine) as session:

        # store user preferences
        preferences = UserPreferencesTable(
            consent=True,
            files_to_ignore=['README.md', 'tmp.log', '.gitignore'],
            file_start_time=datetime.datetime.now(),
            file_end_time=datetime.datetime.now() + timedelta(hours=3)
        )

        # create file reports
        fr1 = create_file_report()
        fr2 = create_file_report()
        fr3 = create_file_report()
        fr4 = create_file_report()
        fr5 = create_file_report()

        # two projects, each with two file reports
        pr1 = create_project_report(fr2, fr3, collaborative=True)
        pr2 = create_project_report(fr4, fr5, collaborative=False)

        # one user report referencing both projects (many-to-many)
        ur1 = UserReportTable(project_reports=[pr1, pr2])

        session.add_all([preferences, fr1, pr1, pr2, ur1])
        session.commit()

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
            "user_report", "user_preferences", "association_table"} <= tables


def test_sample_data_inserted(temp_db):
    # check that data was actually put into the DB
    with Session(temp_db) as session:
        file_count = session.query(FileReportTable).count()
        project_count = session.query(ProjectReportTable).count()
        user_count = session.query(UserReportTable).count()

        assert file_count >= 5  # 5 file reports
        assert project_count == 2  # 2 project reports
        assert user_count == 1  # 1 user report


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


def test_user_preferences_table_exists(temp_db):
    '''
    Verify that UserPreferencesTable exists and is accessible.
    '''
    inspector = inspect(temp_db)
    tables = inspector.get_table_names()
    assert 'user_preferences' in tables


def test_user_preferences_data_inserted(temp_db):
    '''
    Verify that user preferences data was inserted during fixture setup.
    '''
    with Session(temp_db) as session:
        prefs = session.query(UserPreferencesTable).first()
        assert prefs is not None
        assert prefs.consent is True
        assert prefs.files_to_ignore is not None
        assert isinstance(prefs.files_to_ignore, list)
        assert len(prefs.files_to_ignore) == 3
