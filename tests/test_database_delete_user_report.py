def test_delete_user_report_no_related_reports():
    engine = get_engine()
    with Session(engine) as session:
        user_report = UserReportTable(title="Solo", zipped_filepath="/tmp/solo.zip")
        session.add(user_report)
        session.commit()
        solo_id = user_report.id
    assert delete_user_report_and_related_data(report_id=solo_id)
    with Session(engine) as session:
        assert session.get(UserReportTable, solo_id) is None

def test_delete_user_report_multiple_users():
    engine = get_engine()
    with Session(engine) as session:
        pr = ProjectReportTable(project_name="MultiShared")
        u1 = UserReportTable(title="U1", zipped_filepath="/tmp/u1.zip")
        u2 = UserReportTable(title="U2", zipped_filepath="/tmp/u2.zip")
        u3 = UserReportTable(title="U3", zipped_filepath="/tmp/u3.zip")
        u1.project_reports.append(pr)
        u2.project_reports.append(pr)
        u3.project_reports.append(pr)
        session.add_all([u1, u2, u3, pr])
        session.commit()
        pr_id = pr.id
        u2_id = u2.id
    assert delete_user_report_and_related_data(report_id=u2_id)
    with Session(engine) as session:
        assert session.get(ProjectReportTable, pr_id) is not None
        assert session.get(UserReportTable, u2_id) is None

def test_delete_user_report_similar_values():
    engine = get_engine()
    with Session(engine) as session:
        u1 = UserReportTable(title="SameTitle", zipped_filepath="/tmp/same.zip")
        u2 = UserReportTable(title="SameTitle", zipped_filepath="/tmp/same2.zip")
        session.add_all([u1, u2])
        session.commit()
        u1_id = u1.id
        u2_id = u2.id
    # Only the first match should be deleted by title
    assert delete_user_report_and_related_data(title="SameTitle")
    with Session(engine) as session:
        # One should remain
        remaining = session.query(UserReportTable).filter_by(title="SameTitle").all()
        assert len(remaining) == 1
        assert remaining[0].id == u2_id or remaining[0].id == u1_id

def test_delete_user_report_empty_fields():
    engine = get_engine()
    with Session(engine) as session:
        u1 = UserReportTable(title=None, zipped_filepath=None)
        session.add(u1)
        session.commit()
        u1_id = u1.id
    assert delete_user_report_and_related_data(report_id=u1_id)
    with Session(engine) as session:
        assert session.get(UserReportTable, u1_id) is None
def test_shared_project_report_not_deleted():
    engine = get_engine()
    with Session(engine) as session:
        # Create two user reports sharing the same project report
        shared_project = ProjectReportTable(project_name="Shared Project")
        user1 = UserReportTable(title="User1", zipped_filepath="/tmp/u1.zip")
        user2 = UserReportTable(title="User2", zipped_filepath="/tmp/u2.zip")
        user1.project_reports.append(shared_project)
        user2.project_reports.append(shared_project)
        session.add_all([user1, user2, shared_project])
        session.commit()
        shared_id = shared_project.id
        user1_id = user1.id
    # Delete user1
    assert delete_user_report_and_related_data(report_id=user1_id)
    # Check shared project still exists
    with Session(engine) as session:
        assert session.get(ProjectReportTable, shared_id) is not None
        assert session.get(UserReportTable, user1_id) is None
import pytest
from src.database.utils.database_modify import delete_user_report_and_related_data
from src.database.db import get_engine, UserReportTable, ProjectReportTable, FileReportTable, Base
from sqlalchemy.orm import Session

# Helper to setup and teardown DB for tests
def setup_module(module):
    engine = get_engine()
    Base.metadata.create_all(engine)

def teardown_module(module):
    engine = get_engine()
    Base.metadata.drop_all(engine)

def create_sample_data(session):
    # Create sample user report, project report, and file report
    user_report = UserReportTable()
    user_report.title = "Test Report"
    user_report.zipped_filepath = "/tmp/test.zip"
    project_report = ProjectReportTable(project_name="Test Project")
    file_report = FileReportTable(filepath="/tmp/test.py")
    project_report.file_reports.append(file_report)
    user_report.project_reports.append(project_report)
    session.add(user_report)
    session.commit()
    return user_report, project_report, file_report

def test_delete_by_title():
    engine = get_engine()
    with Session(engine) as session:
        user_report, project_report, file_report = create_sample_data(session)
        user_report_id = user_report.id
        # Delete by id
        assert delete_user_report_and_related_data(report_id=user_report_id)
        session.commit()
    with Session(engine) as session:
        assert session.get(UserReportTable, user_report_id) is None
        assert session.query(ProjectReportTable).filter_by(project_name="Test Project").first() is None
        assert session.query(FileReportTable).filter_by(filepath="/tmp/test.py").first() is None

    # Delete by title
    with Session(engine) as session:
        user_report, project_report, file_report = create_sample_data(session)
        assert delete_user_report_and_related_data(title="Test Report")
        session.commit()
    with Session(engine) as session:
        assert session.query(UserReportTable).filter_by(title="Test Report").first() is None
        assert session.query(ProjectReportTable).filter_by(project_name="Test Project").first() is None
        assert session.query(FileReportTable).filter_by(filepath="/tmp/test.py").first() is None

    # Delete by zipped_filepath
    with Session(engine) as session:
        user_report, project_report, file_report = create_sample_data(session)
        assert delete_user_report_and_related_data(zipped_filepath="/tmp/test.zip")
        session.commit()
    with Session(engine) as session:
        assert session.query(UserReportTable).filter_by(zipped_filepath="/tmp/test.zip").first() is None
        assert session.query(ProjectReportTable).filter_by(project_name="Test Project").first() is None
        assert session.query(FileReportTable).filter_by(filepath="/tmp/test.py").first() is None


def test_delete_nonexistent():
    # Should raise ValueError if not found
    with pytest.raises(ValueError):
        delete_user_report_and_related_data(report_id=99999)

def test_delete_without_args():
    # Should raise ValueError if no args
    with pytest.raises(ValueError):
        delete_user_report_and_related_data()
