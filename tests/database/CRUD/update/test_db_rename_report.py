"""
Tests for rename_user_report function
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.infrastructure.database.utils.database_access import get_user_report
from src.infrastructure.database.utils.database_modify import rename_user_report


def test_rename_user_report_success(temp_db):
    ok, msg = rename_user_report(
        "test_user_report", "renamed_portfolio", temp_db)
    assert ok is True
    assert "renamed_portfolio" in msg

    renamed = get_user_report("renamed_portfolio", temp_db)
    assert renamed.report_name == "renamed_portfolio"


def test_rename_user_report_conflict(temp_db):
    from src.infrastructure.database.db import UserReportTable

    with Session(temp_db) as session:
        session.add(UserReportTable(title="existing_portfolio"))
        session.commit()

    ok, msg = rename_user_report(
        "test_user_report", "existing_portfolio", temp_db)
    assert ok is False
    assert "already exists" in msg


def test_rename_user_report_handles_duplicates(temp_db):
    from src.infrastructure.database.db import UserReportTable

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
