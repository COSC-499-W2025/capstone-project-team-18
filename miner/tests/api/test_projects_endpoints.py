"""
Tests for /projects endpoints
"""
import io, datetime
import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session
from urllib.parse import quote
from src.database.api.models import ProjectReportModel

from src.interface.api.routers.util import get_session


@pytest.fixture(autouse=True)
def mock_engine(client, blank_db):
    def fake_get_session():
        with Session(blank_db) as session:
            yield session

    client.app.dependency_overrides[get_session] = fake_get_session
    yield
    client.app.dependency_overrides.clear()


class TestUploadProject:
    """Tests for POST /projects/upload"""

    def test_upload_valid_zip(self, client):
        """Test uploading a valid zip file succeeds"""
        with patch('src.interface.api.routers.projects.start_miner_service') as mock_miner:
            mock_miner.return_value = MagicMock(success=True, project_errors=[])

            response = client.post(
                "/projects/upload",
                files={"file": ("my_project.zip", io.BytesIO(b"PK\x03\x04fake"), "application/zip")}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Project uploaded and analyzed successfully"
            assert data["portfolio_name"] == "my_project"
            mock_miner.assert_called_once()

    def test_upload_with_email(self, client):
        """Test that email query param is passed through to start_miner_service"""
        with patch('src.interface.api.routers.projects.start_miner_service') as mock_miner:
            mock_miner.return_value = MagicMock(success=True, project_errors=[])

            response = client.post(
                "/projects/upload?email=test@example.com",
                files={"file": ("project.zip", io.BytesIO(b"PK\x03\x04fake"), "application/zip")}
            )

            assert response.status_code == 200
            _, kwargs = mock_miner.call_args
            assert kwargs["user_config"].user_email == "test@example.com"

    def test_upload_7z_supported(self, client):
        """Test that .7z files are accepted"""
        with patch('src.interface.api.routers.projects.start_miner_service') as mock_miner:
            mock_miner.return_value = MagicMock(success=True, project_errors=[])

            response = client.post(
                "/projects/upload",
                files={"file": ("project.7z", io.BytesIO(b"fake7z"), "application/x-7z-compressed")}
            )

            assert response.status_code == 200
            assert response.json()["portfolio_name"] == "project"

    def test_upload_unsupported_format_rejected(self, client):
        """Test that unsupported file formats return 400"""
        response = client.post(
            "/projects/upload",
            files={"file": ("project.rar", io.BytesIO(b"content"), "application/x-rar")}
        )

        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()

    def test_upload_no_file_returns_422(self, client):
        """Test that missing file body returns 422"""
        response = client.post("/projects/upload")
        assert response.status_code == 422

    def test_upload_value_error_returns_422(self, client):
        """Test that ValueError from miner returns 422"""
        with patch('src.interface.api.routers.projects.start_miner_service') as mock_miner:
            mock_miner.side_effect = ValueError("No projects found in zip")

            response = client.post(
                "/projects/upload",
                files={"file": ("empty.zip", io.BytesIO(b"PK\x03\x04fake"), "application/zip")}
            )

            assert response.status_code == 422
            assert "No projects found" in response.json()["detail"]

    def test_upload_unexpected_error_returns_500(self, client):
        """Test that unexpected errors return 500"""
        with patch('src.interface.api.routers.projects.start_miner_service') as mock_miner:
            mock_miner.side_effect = Exception("Something went wrong")

            response = client.post(
                "/projects/upload",
                files={"file": ("project.zip", io.BytesIO(b"PK\x03\x04fake"), "application/zip")}
            )

            assert response.status_code == 500
            assert "failed to process" in response.json()["detail"].lower()

    def test_upload_custom_portfolio_name(self, client):
        """Test that a custom portfolio_name overrides the filename"""
        with patch('src.interface.api.routers.projects.start_miner_service') as mock_miner:
            mock_miner.return_value = MagicMock(success=True, project_errors=[])

            response = client.post(
                "/projects/upload?portfolio_name=My+Custom+Portfolio",
                files={"file": ("project.zip", io.BytesIO(b"PK\x03\x04fake"), "application/zip")}
            )

            assert response.status_code == 200
            assert response.json()["portfolio_name"] == "My Custom Portfolio"

def _insert_project(engine, name: str):
    with Session(engine) as session:
        session.add(ProjectReportModel(
            project_name=name,
            user_config_used=None,
            image_data=None,
            statistic={"dummy": True},
            created_at=datetime.datetime.now(),
            last_updated=datetime.datetime.now(),
        ))
        session.commit()


def test_patch_representation_rank_negative_returns_422(client, blank_db):
    _insert_project(blank_db, "Demo Project")

    r = client.patch(
        f"/projects/{quote('Demo Project')}/representation",
        json={"representation_rank": -1},
    )

    assert r.status_code == 422, r.text
    assert "representation_rank" in r.json().get("detail", "")