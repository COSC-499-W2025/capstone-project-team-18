"""
Tests for POST /privacy-consent endpoint
"""
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


class TestPrivacyConsent:
    """Tests for POST /privacy-consent"""

    def test_grant_consent(self, client):
        """Test granting privacy consent creates a config"""
        with patch('src.interface.api.routers.privacy_consent.get_most_recent_user_config') as mock_get, \
             patch('src.interface.api.routers.privacy_consent.save_user_config'):

            mock_get.return_value = None

            response = client.post("/privacy-consent", json={
                "consent": True,
                "user_email": "test@example.com"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["consent"] is True
            assert data["user_email"] == "test@example.com"
            assert "granted" in data["message"].lower()

    def test_revoke_consent(self, client):
        """Test revoking consent returns correct message"""
        with patch('src.interface.api.routers.privacy_consent.get_most_recent_user_config') as mock_get, \
             patch('src.interface.api.routers.privacy_consent.save_user_config'):

            mock_get.return_value = None

            response = client.post("/privacy-consent", json={
                "consent": False,
                "user_email": "test@example.com"
            })

            assert response.status_code == 200
            assert "revoked" in response.json()["message"].lower()

    def test_empty_email_returns_400(self, client):
        """Test that empty email string returns 400"""
        with patch('src.interface.api.routers.privacy_consent.get_most_recent_user_config') as mock_get:
            mock_get.return_value = None

            response = client.post("/privacy-consent", json={
                "consent": True,
                "user_email": ""
            })

            assert response.status_code == 400
            assert "user_email" in response.json()["detail"].lower()

    def test_missing_email_returns_422(self, client):
        """Test that missing email field returns 422"""
        response = client.post("/privacy-consent", json={"consent": True})
        assert response.status_code == 422

    def test_missing_body_returns_422(self, client):
        """Test that empty body returns 422"""
        response = client.post("/privacy-consent", json={})
        assert response.status_code == 422

    def test_updates_existing_config(self, client):
        """Test that an existing config is updated not duplicated"""
        from src.database.api.models import UserConfigModel

        existing = UserConfigModel(id=1, user_email="old@example.com", consent=False)

        with patch('src.interface.api.routers.privacy_consent.get_most_recent_user_config') as mock_get, \
             patch('src.interface.api.routers.privacy_consent.save_user_config'):

            mock_get.return_value = existing

            response = client.post("/privacy-consent", json={
                "consent": True,
                "user_email": "new@example.com"
            })

            assert response.status_code == 200
            assert existing.consent is True
            assert existing.user_email == "new@example.com"

    def test_save_failure_returns_500(self, client):
        """Test that a DB failure returns 500"""
        with patch('src.interface.api.routers.privacy_consent.get_most_recent_user_config') as mock_get, \
             patch('src.interface.api.routers.privacy_consent.save_user_config') as mock_save:

            mock_get.return_value = None
            mock_save.side_effect = Exception("DB error")

            response = client.post("/privacy-consent", json={
                "consent": True,
                "user_email": "test@example.com"
            })

            assert response.status_code == 500
            assert "failed to save" in response.json()["detail"].lower()