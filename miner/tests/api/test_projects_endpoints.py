"""
Tests for /projects endpoints
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session

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

    def test_upload_non_zip_rejected(self, client):
        """Test that non-zip files return 400"""
        response = client.post(
            "/projects/upload",
            files={"file": ("project.tar.gz", io.BytesIO(b"content"), "application/gzip")}
        )

        assert response.status_code == 400
        assert "zip" in response.json()["detail"].lower()

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