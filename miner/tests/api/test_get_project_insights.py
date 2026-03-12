"""
Tests for GET /projects/{project_name}/insights
"""

import datetime
import pytest
from unittest.mock import MagicMock, patch
from urllib.parse import quote

from sqlmodel import Session

from src.database.api.models import ProjectReportModel
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


def test_get_project_insights_returns_200_with_insights(client, blank_db):
    _insert_project(blank_db, "MyProject")

    with patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen:

        mock_get.return_value = MagicMock()
        mock_gen.return_value = [
            MagicMock(message="You wrote 80% code. What features did you build?"),
            MagicMock(message="You were a primary contributor. What challenges did you tackle?"),
        ]

        response = client.get(f"/projects/{quote('MyProject')}/insights")

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "MyProject"
    assert len(data["insights"]) == 2
    assert data["insights"][0]["message"] == "You wrote 80% code. What features did you build?"


def test_get_project_insights_returns_empty_list_when_no_insights(client, blank_db):
    _insert_project(blank_db, "QuietProject")

    with patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen:

        mock_get.return_value = MagicMock()
        mock_gen.return_value = []

        response = client.get(f"/projects/{quote('QuietProject')}/insights")

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "QuietProject"
    assert data["insights"] == []


def test_get_project_insights_returns_404_when_project_not_found(client, blank_db):
    with patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get:
        mock_get.return_value = None

        response = client.get("/projects/DoesNotExist/insights")

    assert response.status_code == 404
    assert "DoesNotExist" in response.json()["detail"]


def test_get_project_insights_url_decodes_project_name(client, blank_db):
    _insert_project(blank_db, "My Cool Project")

    with patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen:

        mock_get.return_value = MagicMock()
        mock_gen.return_value = []

        response = client.get(f"/projects/{quote('My Cool Project')}/insights")

    assert response.status_code == 200
    assert response.json()["project_name"] == "My Cool Project"


def test_get_project_insights_passes_report_to_generator(client, blank_db):
    _insert_project(blank_db, "ReportProject")

    mock_report = MagicMock()

    with patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen:

        mock_get.return_value = mock_report
        mock_gen.return_value = []

        client.get(f"/projects/{quote('ReportProject')}/insights")

        mock_gen.assert_called_once_with(mock_report)


def test_get_project_insights_returns_500_on_generator_error(client, blank_db):
    _insert_project(blank_db, "BrokenProject")

    with patch("src.interface.api.routers.insights.get_project_report_by_name") as mock_get, \
         patch("src.interface.api.routers.insights.InsightGenerator.generate") as mock_gen:

        mock_get.return_value = MagicMock()
        mock_gen.side_effect = RuntimeError("something went wrong")

        response = client.get(f"/projects/{quote('BrokenProject')}/insights")

    assert response.status_code == 500
    assert "insights" in response.json()["detail"].lower()
