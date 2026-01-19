"""
Tests the delete_user_report_and_related_data() function
"""

import pytest
from sqlalchemy.orm import Session
from src.database.models import FileReportTable, ProjectReportTable, UserReportTable
from src.database.utils.database_modify import delete_user_report_and_related_data


def test_delete_user_report_no_related_reports(blank_db):
    with Session(blank_db) as session:
        user_report = UserReportTable(title="Solo")
        session.add(user_report)
        session.commit()
        solo_id = user_report.id
    assert delete_user_report_and_related_data(
        report_id=solo_id, engine=blank_db)
    with Session(blank_db) as session:
        assert session.get(UserReportTable, solo_id) is None


def test_delete_user_report_multiple_users(blank_db):
    with Session(blank_db) as session:
        pr = ProjectReportTable(project_name="MultiShared")
        u1 = UserReportTable(title="U1")
        u2 = UserReportTable(title="U2")
        u3 = UserReportTable(title="U3")
        u1.project_reports.append(pr)
        u2.project_reports.append(pr)
        u3.project_reports.append(pr)
        session.add_all([u1, u2, u3, pr])
        session.commit()
        pr_id = pr.id
        u2_id = u2.id
    assert delete_user_report_and_related_data(
        report_id=u2_id, engine=blank_db)
    with Session(blank_db) as session:
        assert session.get(ProjectReportTable, pr_id) is not None
        assert session.get(UserReportTable, u2_id) is None


def test_delete_user_report_similar_values(blank_db):
    with Session(blank_db) as session:
        u1 = UserReportTable(title="SameTitle")
        u2 = UserReportTable(title="SameTitle")
        session.add_all([u1, u2])
        session.commit()
        u1_id = u1.id
        u2_id = u2.id
    # Only the first match should be deleted by title
    assert delete_user_report_and_related_data(
        title="SameTitle", engine=blank_db)
    with Session(blank_db) as session:
        # One should remain
        remaining = session.query(UserReportTable).filter_by(
            title="SameTitle").all()
        assert len(remaining) == 1
        assert remaining[0].id == u2_id or remaining[0].id == u1_id


def test_delete_user_report_empty_fields(blank_db):
    with Session(blank_db) as session:
        u1 = UserReportTable(title=None)
        session.add(u1)
        session.commit()
        u1_id = u1.id
    assert delete_user_report_and_related_data(
        report_id=u1_id, engine=blank_db)
    with Session(blank_db) as session:
        assert session.get(UserReportTable, u1_id) is None


def test_shared_project_report_not_deleted(blank_db):
    with Session(blank_db) as session:
        # Create two user reports sharing the same project report
        shared_project = ProjectReportTable(project_name="Shared Project")
        user1 = UserReportTable(title="User1")
        user2 = UserReportTable(title="User2")
        user1.project_reports.append(shared_project)
        user2.project_reports.append(shared_project)
        session.add_all([user1, user2, shared_project])
        session.commit()
        shared_id = shared_project.id
        user1_id = user1.id
    # Delete user1
    assert delete_user_report_and_related_data(
        report_id=user1_id, engine=blank_db)
    # Check shared project still exists
    with Session(blank_db) as session:
        assert session.get(ProjectReportTable, shared_id) is not None
        assert session.get(UserReportTable, user1_id) is None


def test_delete_by_id(blank_db):
    with Session(blank_db) as session:
        user_report = UserReportTable()
        user_report.title = "Test Report"
        project_report = ProjectReportTable(project_name="Test Project")
        file_report = FileReportTable(filepath="/tmp/test.py")
        project_report.file_reports.append(file_report)
        user_report.project_reports.append(project_report)
        session.add(user_report)
        session.commit()
        user_report_id = user_report.id
        # Delete by id
        assert delete_user_report_and_related_data(
            report_id=user_report_id, engine=blank_db)
        session.commit()

    with Session(blank_db) as session:
        assert session.get(UserReportTable, user_report_id) is None
        assert session.query(ProjectReportTable).filter_by(
            project_name="Test Project").first() is None
        assert session.query(FileReportTable).filter_by(
            filepath="/tmp/test.py").first() is None


def test_delete_by_title(temp_db):
   # Delete by title
    with Session(temp_db) as session:
        assert delete_user_report_and_related_data(
            title="test_user_report", engine=temp_db)
        session.commit()

    with Session(temp_db) as session:
        assert session.query(UserReportTable).filter_by(
            title="test_user_report").first() is None
        assert session.query(ProjectReportTable).filter_by(
            project_name="Project1").first() is None
        assert session.query(FileReportTable).filter_by(
            filepath="file1.py").first() is None


def test_delete_nonexistent(temp_db):
    # Should raise ValueError if not found
    with pytest.raises(ValueError):
        delete_user_report_and_related_data(report_id=99999, engine=temp_db)


def test_delete_without_args(temp_db):
    # Should raise ValueError if no args
    with pytest.raises(ValueError):
        delete_user_report_and_related_data(engine=temp_db)
