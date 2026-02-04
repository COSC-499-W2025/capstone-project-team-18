"""
'Meta' tests in the db. Both in the way that we check the schema
and also in that we check to see if our fixtures work
"""
from pathlib import Path
from alembic import command
from alembic.config import Config


from sqlalchemy import inspect
from sqlalchemy.orm import Session

from src.database.models import FileReportTable, ProjectReportTable, UserReportTable
from src.core.statistic import FileStatCollection, ProjectStatCollection, UserStatCollection


def test_tables_exist(temp_db):
    '''verify that all tables are present in the DB'''
    inspector = inspect(temp_db)
    tables = set(inspector.get_table_names())
    assert {"file_report", "portfolio", "proj_user_assoc", "project_report",
            "resume_item", "resume_proj_assoc", "resume", "user_report", } <= tables
    assert "invalid_table" not in tables


def test_sample_data_inserted(temp_db):
    '''check that data was actually put into the DB'''
    with Session(temp_db) as session:
        file_count = session.query(FileReportTable).count()
        project_count = session.query(ProjectReportTable).count()
        user_count = session.query(UserReportTable).count()

        assert file_count == 4  # 4 file reports
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


def test_exists_file_report_stat_cols(temp_db):
    """
    Test that all of the statistics defined in
    file_stat_collection.py are present as columns
    in the database
    """
    file_report_table = FileReportTable.__table__

    for stat in FileStatCollection:
        stat_col_name = stat.value.name.lower()

        assert stat_col_name in file_report_table.c, (
            f"Missing column '{stat_col_name}' in FileReport table."
        )


def test_exists_project_report_stat_cols(temp_db):
    """
    Test that all of the statistics defined in
    project_stat_collection.py are present as columns
    in the database
    """
    project_report_table = ProjectReportTable.__table__

    for stat in ProjectStatCollection:
        stat_col_name = stat.value.name.lower()

        assert stat_col_name in project_report_table.c, (
            f"Missing column '{stat_col_name}' in ProjectReport table."
        )


def test_exists_user_report_stat_cols(temp_db):
    """
    Test that all of the statistics defined in
    project_stat_collection.py are present as columns
    in the database
    """
    user_report_table = UserReportTable.__table__

    for stat in UserStatCollection:
        stat_col_name = stat.value.name.lower()
        assert stat_col_name in user_report_table.c, (
            f"Missing column '{stat_col_name}' in UserReport table."
        )


def test_project_to_user_many_to_many(temp_db):
    '''
    Check that bi-directional many-to-many relationship of
    UserReport <-> ProjectReport is configured properly
    '''
    with Session(temp_db) as session:
        user = session.query(UserReportTable).first()
        assert user is not None
        assert len(user.project_reports) == 2
        # verify they work in the other direction too
        for p in user.project_reports:
            assert user in p.user_reports


def test_proj_user_assoc_table(temp_db):
    '''
    Verify that the proj_user_assoc table correctly manages
    a *..* relationship between the project_report and
    user_report tables.
    '''
    inspector = inspect(temp_db)
    fks = inspector.get_foreign_keys("proj_user_assoc")
    fk_map = {fk["constrained_columns"][0]: fk["referred_table"] for fk in fks}
    assert fk_map == {"project_report_id": "project_report",
                      "user_report_id": "user_report", }

    pk = inspector.get_pk_constraint("proj_user_assoc")
    assert set(pk["constrained_columns"]) == {
        "project_report_id", "user_report_id", }


# TODO: Once the resume and portfolio tables are more fleshed
# out, we'll need tests to verify their config, relationships, etc.
