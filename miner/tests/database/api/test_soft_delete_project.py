"""
Unit tests for soft-delete CRUD operations on ProjectReportModel.

Covers:
- soft_delete_project_report_by_name
- get_all_project_report_models (is_deleted filter)
- get_project_report_model_by_name (no filter — used by resume/portfolio)
- save_project_report resurrection (re-upload of deleted project)
"""
import datetime
import pytest
from sqlmodel import Session, select, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from src.database.api.models import ProjectReportModel
from src.database.api.CRUD.projects import (
    get_all_project_report_models,
    get_project_report_model_by_name,
    soft_delete_project_report_by_name,
    save_project_report,
)
from src.core.report import FileReport, ProjectReport
from src.core.statistic import StatisticIndex, Statistic, FileStatCollection
from src.core.statistic.statistic_models import FileDomain


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """In-memory SQLite database, reset for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def _insert(engine, name: str, is_deleted: bool = False) -> None:
    with Session(engine) as session:
        session.add(ProjectReportModel(
            project_name=name,
            statistic={"dummy": True},
            created_at=datetime.datetime.now(),
            last_updated=datetime.datetime.now(),
            is_deleted=is_deleted,
        ))
        session.commit()


def _row(engine, name: str) -> ProjectReportModel | None:
    """Direct DB lookup, ignoring is_deleted."""
    with Session(engine) as session:
        return session.exec(
            select(ProjectReportModel).where(ProjectReportModel.project_name == name)
        ).first()


def _make_project_report(name: str) -> ProjectReport:
    """Minimal ProjectReport with one file, sufficient for save_project_report."""
    fr = FileReport(
        StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 10),
            Statistic(FileStatCollection.DATE_CREATED.value, datetime.datetime(2025, 1, 1)),
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime.datetime(2025, 1, 2)),
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 100),
            Statistic(FileStatCollection.TYPE_OF_FILE.value, FileDomain.CODE),
        ]),
        "main.py",
        is_info_file=False,
        file_hash=b"abc",
        project_name=name,
    )
    return ProjectReport(file_reports=[fr], project_name=name)


# ---------------------------------------------------------------------------
# soft_delete_project_report_by_name
# ---------------------------------------------------------------------------

class TestSoftDeleteCRUD:

    def test_returns_true_for_existing_project(self, db):
        _insert(db, "Alpha")

        with Session(db) as session:
            result = soft_delete_project_report_by_name(session, "Alpha")
            session.commit()

        assert result is True

    def test_sets_is_deleted_flag(self, db):
        _insert(db, "Beta")

        with Session(db) as session:
            soft_delete_project_report_by_name(session, "Beta")
            session.commit()

        row = _row(db, "Beta")
        assert row is not None
        assert row.is_deleted is True

    def test_row_still_exists_after_soft_delete(self, db):
        _insert(db, "Gamma")

        with Session(db) as session:
            soft_delete_project_report_by_name(session, "Gamma")
            session.commit()

        assert _row(db, "Gamma") is not None

    def test_returns_false_for_missing_project(self, db):
        with Session(db) as session:
            result = soft_delete_project_report_by_name(session, "NoSuchProject")
            session.commit()

        assert result is False

    def test_does_not_affect_other_projects(self, db):
        _insert(db, "ToDelete")
        _insert(db, "ToKeep")

        with Session(db) as session:
            soft_delete_project_report_by_name(session, "ToDelete")
            session.commit()

        keep_row = _row(db, "ToKeep")
        assert keep_row is not None
        assert keep_row.is_deleted is False


# ---------------------------------------------------------------------------
# get_all_project_report_models — must exclude soft-deleted rows
# ---------------------------------------------------------------------------

class TestGetAllProjectsFilter:

    def test_excludes_soft_deleted_projects(self, db):
        _insert(db, "Visible")
        _insert(db, "Hidden", is_deleted=True)

        with Session(db) as session:
            results = get_all_project_report_models(session)

        names = [r.project_name for r in results]
        assert "Visible" in names
        assert "Hidden" not in names

    def test_returns_empty_list_when_all_deleted(self, db):
        _insert(db, "X", is_deleted=True)
        _insert(db, "Y", is_deleted=True)

        with Session(db) as session:
            results = get_all_project_report_models(session)

        assert results == []

    def test_returns_all_when_none_deleted(self, db):
        _insert(db, "A")
        _insert(db, "B")
        _insert(db, "C")

        with Session(db) as session:
            results = get_all_project_report_models(session)

        assert len(results) == 3


# ---------------------------------------------------------------------------
# get_project_report_model_by_name — must NOT filter is_deleted
# (resume refresh and portfolio export still need the row)
# ---------------------------------------------------------------------------

class TestGetByNameIgnoresDeleteFlag:

    def test_finds_active_project(self, db):
        _insert(db, "Active")

        with Session(db) as session:
            result = get_project_report_model_by_name(session, "Active")

        assert result is not None
        assert result.project_name == "Active"

    def test_still_finds_soft_deleted_project(self, db):
        """Resume refresh depends on finding deleted projects — must not filter."""
        _insert(db, "Deleted", is_deleted=True)

        with Session(db) as session:
            result = get_project_report_model_by_name(session, "Deleted")

        assert result is not None
        assert result.is_deleted is True

    def test_returns_none_for_truly_absent_project(self, db):
        with Session(db) as session:
            result = get_project_report_model_by_name(session, "NeverExisted")

        assert result is None


# ---------------------------------------------------------------------------
# save_project_report — resurrection logic
# ---------------------------------------------------------------------------

class TestResurrection:

    def test_reupload_clears_is_deleted_flag(self, db):
        """Re-uploading a soft-deleted project should resurrect it."""
        _insert(db, "Phoenix", is_deleted=True)

        project_report = _make_project_report("Phoenix")
        with Session(db) as session:
            save_project_report(session, project_report, user_config_id=None)
            session.commit()

        row = _row(db, "Phoenix")
        assert row is not None
        assert row.is_deleted is False

    def test_resurrected_project_appears_in_list(self, db):
        """After resurrection, project must be visible in get_all_project_report_models."""
        _insert(db, "Lazarus", is_deleted=True)

        project_report = _make_project_report("Lazarus")
        with Session(db) as session:
            save_project_report(session, project_report, user_config_id=None)
            session.commit()

        with Session(db) as session:
            results = get_all_project_report_models(session)

        names = [r.project_name for r in results]
        assert "Lazarus" in names

    def test_reupload_updates_statistic(self, db):
        """Re-upload should replace the statistic payload."""
        _insert(db, "Reborn", is_deleted=True)

        # Build a ProjectReport whose serialized statistic will differ
        project_report = _make_project_report("Reborn")
        with Session(db) as session:
            saved = save_project_report(session, project_report, user_config_id=None)
            session.commit()
            saved_stat = saved.statistic

        # The old dummy statistic should have been replaced
        assert saved_stat != {"dummy": True}
