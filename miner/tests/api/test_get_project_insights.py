"""
Tests for GET /projects/{project_name}/insights
"""

import datetime
import pytest
from unittest.mock import MagicMock, patch
from urllib.parse import quote

from sqlmodel import Session

from src.database.api.models import ProjectReportModel, ProjectInsightsModel
from src.interface.api.routers.util import get_session


def _insert_project(engine, name: str):
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


def _insert_cached_insights(engine, project_name: str, messages: list[str]):
    with Session(engine) as session:
        session.add(ProjectInsightsModel(
            project_name=project_name,
            insights=messages,
        ))
        session.commit()


# ---------------------------------------------------------------------------
# Cache miss: insights generated and saved on first call
# ---------------------------------------------------------------------------

def test_get_project_insights_generates_and_returns_insights_on_cache_miss(client, blank_db):
    _insert_project(blank_db, "NewProject")

    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen, \
         patch("src.interface.api.routers.insights.save_project_insights") as mock_save:

        mock_cached.return_value = None
        mock_get.return_value = MagicMock()
        mock_gen.return_value = [
            MagicMock(message="You wrote 80% of this project."),
            MagicMock(message="You used Python and FastAPI."),
        ]

        response = client.get(f"/projects/{quote('NewProject')}/insights")

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "NewProject"
    assert len(data["insights"]) == 2
    assert data["insights"][0]["message"] == "You wrote 80% of this project."
    mock_save.assert_called_once()


def test_get_project_insights_saves_insights_to_db_on_cache_miss(client, blank_db):
    _insert_project(blank_db, "SaveProject")

    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen, \
         patch("src.interface.api.routers.insights.save_project_insights") as mock_save:

        mock_cached.return_value = None
        mock_get.return_value = MagicMock()
        mock_gen.return_value = [MagicMock(message="Some insight.")]

        client.get(f"/projects/{quote('SaveProject')}/insights")

        mock_save.assert_called_once()


def test_get_project_insights_passes_correct_messages_to_save(client, blank_db):
    _insert_project(blank_db, "CheckSave")

    captured = {}

    def fake_save(session, name, messages):
        captured["name"] = name
        captured["messages"] = messages

    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen, \
         patch("src.interface.api.routers.insights.save_project_insights", side_effect=fake_save):

        mock_cached.return_value = None
        mock_get.return_value = MagicMock()
        mock_gen.return_value = [
            MagicMock(message="Insight A"),
            MagicMock(message="Insight B"),
        ]

        client.get(f"/projects/{quote('CheckSave')}/insights")

    assert captured["name"] == "CheckSave"
    assert captured["messages"] == ["Insight A", "Insight B"]


# ---------------------------------------------------------------------------
# Cache hit: cached insights returned without calling the generator
# ---------------------------------------------------------------------------

def test_get_project_insights_returns_cached_insights(client, blank_db):
    _insert_project(blank_db, "CachedProject")
    _insert_cached_insights(blank_db, "CachedProject", ["Cached insight one.", "Cached insight two."])

    with patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen:
        response = client.get(f"/projects/{quote('CachedProject')}/insights")
        mock_gen.assert_not_called()

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "CachedProject"
    assert len(data["insights"]) == 2
    assert data["insights"][0]["message"] == "Cached insight one."
    assert data["insights"][1]["message"] == "Cached insight two."


def test_get_project_insights_does_not_call_generator_on_cache_hit(client, blank_db):
    _insert_project(blank_db, "HitProject")
    _insert_cached_insights(blank_db, "HitProject", ["Only from cache."])

    with patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get:

        response = client.get(f"/projects/{quote('HitProject')}/insights")

        mock_gen.assert_not_called()
        mock_get.assert_not_called()

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_get_project_insights_returns_404_when_project_not_found(client, blank_db):
    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get:

        mock_cached.return_value = None
        mock_get.return_value = None

        response = client.get("/projects/DoesNotExist/insights")

    assert response.status_code == 404
    assert "DoesNotExist" in response.json()["message"]


def test_get_project_insights_returns_500_on_generator_error(client, blank_db):
    _insert_project(blank_db, "BrokenProject")

    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen:

        mock_cached.return_value = None
        mock_get.return_value = MagicMock()
        mock_gen.side_effect = RuntimeError("something went wrong")

        response = client.get(f"/projects/{quote('BrokenProject')}/insights")

    assert response.status_code == 500
    assert "insights" in response.json()["detail"].lower()


def test_get_project_insights_returns_empty_list_when_no_insights_generated(client, blank_db):
    _insert_project(blank_db, "QuietProject")

    with patch("src.interface.api.routers.insights.get_project_insights") as mock_cached, \
         patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen, \
         patch("src.interface.api.routers.insights.save_project_insights"):

        mock_cached.return_value = None
        mock_get.return_value = MagicMock()
        mock_gen.return_value = []

        response = client.get(f"/projects/{quote('QuietProject')}/insights")

    assert response.status_code == 200
    assert response.json()["insights"] == []


def test_get_project_insights_url_decodes_project_name(client, blank_db):
    _insert_project(blank_db, "My Cool Project")
    _insert_cached_insights(blank_db, "My Cool Project", ["Great work!"])

    response = client.get(f"/projects/{quote('My Cool Project')}/insights")

    assert response.status_code == 200
    assert response.json()["project_name"] == "My Cool Project"
