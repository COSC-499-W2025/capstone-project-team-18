"""
Tests for POST /projects/{project_name}/insights/dismiss
and dismiss-filtering in GET /projects/{project_name}/insights.
"""

import datetime
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest
from sqlmodel import Session

from src.database.api.models import (
    DismissedInsightModel,
    ProjectInsightsModel,
    ProjectReportModel,
    UserConfigModel,
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


def _insert_ml_consent(engine, enabled: bool) -> None:
    with Session(engine) as session:
        session.add(UserConfigModel(
            consent=True,
            ml_consent=enabled,
            user_email="test@example.com",
        ))
        session.commit()


def _insert_cached_insights(engine, project_name: str, messages: list[str]) -> None:
    with Session(engine) as session:
        session.add(ProjectInsightsModel(
            project_name=project_name,
            insights=messages,
        ))
        session.commit()


def _insert_dismissed(engine, project_name: str, message: str) -> None:
    with Session(engine) as session:
        session.add(DismissedInsightModel(
            project_name=project_name,
            message=message,
        ))
        session.commit()


# ── POST /projects/{name}/insights/dismiss ────────────────────────────────────


def test_dismiss_returns_200_and_dismissed_true_for_known_project(client, blank_db):
    _insert_project(blank_db, "Proj1")

    response = client.post(
        f"/projects/{quote('Proj1')}/insights/dismiss",
        json={"message": "Some insight"},
    )

    assert response.status_code == 200
    assert response.json() == {"dismissed": True}


def test_dismiss_returns_404_for_unknown_project(client, blank_db):
    response = client.post(
        "/projects/NoSuchProject/insights/dismiss",
        json={"message": "irrelevant"},
    )

    assert response.status_code == 404


def test_dismiss_url_decodes_project_name(client, blank_db):
    _insert_project(blank_db, "My Cool Project")

    response = client.post(
        f"/projects/{quote('My Cool Project')}/insights/dismiss",
        json={"message": "some prompt"},
    )

    assert response.status_code == 200


def test_dismiss_is_idempotent_returns_200_on_repeated_call(client, blank_db):
    _insert_project(blank_db, "Proj2")
    payload = {"message": "Same insight"}

    r1 = client.post(f"/projects/{quote('Proj2')}/insights/dismiss", json=payload)
    r2 = client.post(f"/projects/{quote('Proj2')}/insights/dismiss", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200


def test_dismiss_persists_to_database(client, blank_db):
    _insert_project(blank_db, "Proj3")

    client.post(
        f"/projects/{quote('Proj3')}/insights/dismiss",
        json={"message": "Persisted insight"},
    )

    with Session(blank_db) as session:
        from sqlmodel import select
        row = session.exec(
            select(DismissedInsightModel).where(
                DismissedInsightModel.project_name == "Proj3",
                DismissedInsightModel.message == "Persisted insight",
            )
        ).first()

    assert row is not None


# ── GET filtering: dismissed insights removed from cache-hit response ─────────


def test_get_filters_dismissed_insight_from_cache_hit(client, blank_db):
    _insert_project(blank_db, "CacheProj")
    _insert_ml_consent(blank_db, True)
    _insert_cached_insights(blank_db, "CacheProj", ["Keep me", "Dismiss me"])
    _insert_dismissed(blank_db, "CacheProj", "Dismiss me")

    response = client.get(f"/projects/{quote('CacheProj')}/insights")

    assert response.status_code == 200
    messages = [i["message"] for i in response.json()["insights"]]
    assert "Keep me" in messages
    assert "Dismiss me" not in messages


def test_get_returns_empty_list_when_all_cached_insights_dismissed(client, blank_db):
    _insert_project(blank_db, "AllGoneProj")
    _insert_ml_consent(blank_db, True)
    _insert_cached_insights(blank_db, "AllGoneProj", ["Insight A", "Insight B"])
    _insert_dismissed(blank_db, "AllGoneProj", "Insight A")
    _insert_dismissed(blank_db, "AllGoneProj", "Insight B")

    response = client.get(f"/projects/{quote('AllGoneProj')}/insights")

    assert response.status_code == 200
    assert response.json()["insights"] == []


def test_get_returns_undismissed_insights_untouched(client, blank_db):
    _insert_project(blank_db, "PartialProj")
    _insert_ml_consent(blank_db, True)
    _insert_cached_insights(blank_db, "PartialProj", ["A", "B", "C"])
    _insert_dismissed(blank_db, "PartialProj", "B")

    response = client.get(f"/projects/{quote('PartialProj')}/insights")

    messages = [i["message"] for i in response.json()["insights"]]
    assert "A" in messages
    assert "C" in messages
    assert "B" not in messages


# ── GET filtering: dismissed insights removed from cache-miss (generated) path ─


def test_get_filters_dismissed_insight_from_generated_insights(client, blank_db):
    _insert_project(blank_db, "GenProj")
    _insert_dismissed(blank_db, "GenProj", "Dismissed prompt")

    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen, \
         patch("src.interface.api.routers.insights.save_project_insights"):

        mock_cached.return_value = None
        mock_get.return_value = MagicMock()
        mock_gen.return_value = [
            MagicMock(message="Keep this prompt"),
            MagicMock(message="Dismissed prompt"),
        ]

        response = client.get(f"/projects/{quote('GenProj')}/insights")

    assert response.status_code == 200
    messages = [i["message"] for i in response.json()["insights"]]
    assert "Keep this prompt" in messages
    assert "Dismissed prompt" not in messages


def test_get_returns_empty_list_when_all_generated_insights_dismissed(client, blank_db):
    _insert_project(blank_db, "AllDismissedGen")
    _insert_dismissed(blank_db, "AllDismissedGen", "Prompt A")
    _insert_dismissed(blank_db, "AllDismissedGen", "Prompt B")

    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen, \
         patch("src.interface.api.routers.insights.save_project_insights"):

        mock_cached.return_value = None
        mock_get.return_value = MagicMock()
        mock_gen.return_value = [
            MagicMock(message="Prompt A"),
            MagicMock(message="Prompt B"),
        ]

        response = client.get(f"/projects/{quote('AllDismissedGen')}/insights")

    assert response.status_code == 200
    assert response.json()["insights"] == []


# ── Integration: dismiss via endpoint then verify GET filters it ──────────────


def test_dismissed_insight_does_not_appear_in_subsequent_get(client, blank_db):
    _insert_project(blank_db, "IntegProj")
    _insert_ml_consent(blank_db, True)
    _insert_cached_insights(blank_db, "IntegProj", ["Stay", "Go away"])

    client.post(
        f"/projects/{quote('IntegProj')}/insights/dismiss",
        json={"message": "Go away"},
    )

    response = client.get(f"/projects/{quote('IntegProj')}/insights")
    messages = [i["message"] for i in response.json()["insights"]]

    assert "Stay" in messages
    assert "Go away" not in messages


def test_dismissing_all_insights_via_endpoint_leaves_get_empty(client, blank_db):
    _insert_project(blank_db, "EmptyAfterDismiss")
    _insert_ml_consent(blank_db, True)
    _insert_cached_insights(blank_db, "EmptyAfterDismiss", ["Only one"])

    client.post(
        f"/projects/{quote('EmptyAfterDismiss')}/insights/dismiss",
        json={"message": "Only one"},
    )

    response = client.get(f"/projects/{quote('EmptyAfterDismiss')}/insights")
    assert response.json()["insights"] == []
