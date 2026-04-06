"""
Tests for the dismiss-insight CRUD functions:
  - get_dismissed_insight_messages
  - dismiss_project_insight
"""

import datetime

import pytest
from sqlmodel import Session, select

from src.database.api.models import DismissedInsightModel, ProjectReportModel
from src.database.api.CRUD.insights import (
    dismiss_project_insight,
    get_dismissed_insight_messages,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _insert_project(engine, name: str) -> None:
    with Session(engine) as session:
        session.add(ProjectReportModel(
            project_name=name,
            user_config_used=None,
            image_data=None,
            statistic={},
            created_at=datetime.datetime.now(),
            last_updated=datetime.datetime.now(),
        ))
        session.commit()


def _insert_dismissed(engine, project_name: str, message: str) -> None:
    with Session(engine) as session:
        session.add(DismissedInsightModel(
            project_name=project_name,
            message=message,
        ))
        session.commit()


def _count_dismissed_rows(engine, project_name: str, message: str) -> int:
    with Session(engine) as session:
        return len(session.exec(
            select(DismissedInsightModel).where(
                DismissedInsightModel.project_name == project_name,
                DismissedInsightModel.message == message,
            )
        ).all())


# ── get_dismissed_insight_messages ───────────────────────────────────────────


def test_get_dismissed_messages_returns_empty_set_when_none_dismissed(blank_db):
    _insert_project(blank_db, "Alpha")
    with Session(blank_db) as session:
        result = get_dismissed_insight_messages(session, "Alpha")
    assert result == set()


def test_get_dismissed_messages_returns_set_of_dismissed_messages(blank_db):
    _insert_project(blank_db, "Beta")
    _insert_dismissed(blank_db, "Beta", "Insight A")
    _insert_dismissed(blank_db, "Beta", "Insight B")

    with Session(blank_db) as session:
        result = get_dismissed_insight_messages(session, "Beta")

    assert result == {"Insight A", "Insight B"}


def test_get_dismissed_messages_excludes_other_projects(blank_db):
    _insert_project(blank_db, "Gamma")
    _insert_project(blank_db, "Delta")
    _insert_dismissed(blank_db, "Gamma", "For Gamma only")
    _insert_dismissed(blank_db, "Delta", "For Delta only")

    with Session(blank_db) as session:
        result = get_dismissed_insight_messages(session, "Gamma")

    assert "For Gamma only" in result
    assert "For Delta only" not in result


def test_get_dismissed_messages_returns_empty_set_for_unknown_project(blank_db):
    with Session(blank_db) as session:
        result = get_dismissed_insight_messages(session, "DoesNotExist")
    assert result == set()


# ── dismiss_project_insight ───────────────────────────────────────────────────


def test_dismiss_creates_a_row_that_appears_in_get(blank_db):
    _insert_project(blank_db, "Epsilon")

    with Session(blank_db) as session:
        dismiss_project_insight(session, "Epsilon", "Some prompt")
        session.commit()

    with Session(blank_db) as session:
        result = get_dismissed_insight_messages(session, "Epsilon")

    assert "Some prompt" in result


def test_dismiss_is_idempotent_no_duplicate_rows(blank_db):
    _insert_project(blank_db, "Zeta")

    with Session(blank_db) as session:
        dismiss_project_insight(session, "Zeta", "Repeated prompt")
        dismiss_project_insight(session, "Zeta", "Repeated prompt")
        session.commit()

    assert _count_dismissed_rows(blank_db, "Zeta", "Repeated prompt") == 1


def test_dismiss_allows_multiple_different_messages_for_same_project(blank_db):
    _insert_project(blank_db, "Eta")

    with Session(blank_db) as session:
        dismiss_project_insight(session, "Eta", "Prompt X")
        dismiss_project_insight(session, "Eta", "Prompt Y")
        session.commit()

    with Session(blank_db) as session:
        result = get_dismissed_insight_messages(session, "Eta")

    assert result == {"Prompt X", "Prompt Y"}


def test_dismiss_allows_same_message_text_across_different_projects(blank_db):
    _insert_project(blank_db, "Theta")
    _insert_project(blank_db, "Iota")

    with Session(blank_db) as session:
        dismiss_project_insight(session, "Theta", "Shared prompt")
        dismiss_project_insight(session, "Iota", "Shared prompt")
        session.commit()

    with Session(blank_db) as session:
        theta = get_dismissed_insight_messages(session, "Theta")
        iota = get_dismissed_insight_messages(session, "Iota")

    assert "Shared prompt" in theta
    assert "Shared prompt" in iota


def test_dismiss_sets_dismissed_at_timestamp(blank_db):
    _insert_project(blank_db, "Kappa")
    before = datetime.datetime.now()

    with Session(blank_db) as session:
        dismiss_project_insight(session, "Kappa", "Timed prompt")
        session.commit()

    after = datetime.datetime.now()

    with Session(blank_db) as session:
        row = session.exec(
            select(DismissedInsightModel).where(
                DismissedInsightModel.project_name == "Kappa"
            )
        ).first()

    assert row is not None
    assert before <= row.dismissed_at <= after
