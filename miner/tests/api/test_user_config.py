"""
Tests for /user-config endpoints
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


class TestGetUserConfig:
    """Tests for GET /user-config"""

    def test_get_user_config_success(self, client):
        """Test retrieving user config with resume config"""
        # Use real database instead of mocks
        response = client.get("/user-config")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "consent" in data
        assert "resume_config" in data

    def test_get_user_config_with_data(self, client):
        """Test retrieving user config after setting education/awards"""
        # First, create config with data
        client.put("/user-config", json={
            "consent": True,
            "user_email": "test@example.com",
            "github": "testuser",
            "resume_config": {
                "education": ["BSc Computer Science, UBC, 2024"],
                "awards": ["Dean's List 2023"]
            }
        })

        # Now retrieve it
        response = client.get("/user-config")

        assert response.status_code == 200
        data = response.json()
        assert data["user_email"] == "test@example.com"
        assert data["resume_config"]["education"] == ["BSc Computer Science, UBC, 2024"]
        assert data["resume_config"]["awards"] == ["Dean's List 2023"]


class TestUpdateUserConfig:
    """Tests for PUT /user-config"""

    def test_update_user_config_creates_resume_config(self, client):
        """Test updating user config creates new resume config if it doesn't exist"""
        response = client.put("/user-config", json={
            "consent": True,
            "user_email": "test@example.com",
            "github": "testuser",
            "resume_config": {
                "education": ["BSc CS, UBC, 2024"],
                "awards": ["Dean's List"]
            }
        })

        assert response.status_code == 200
        data = response.json()
        assert data["resume_config"] is not None
        assert data["resume_config"]["education"] == ["BSc CS, UBC, 2024"]
        assert data["resume_config"]["awards"] == ["Dean's List"]

    def test_update_user_config_updates_existing_resume_config(self, client):
        """Test updating user config updates existing resume config"""
        # First create
        client.put("/user-config", json={
            "consent": True,
            "user_email": "test@example.com",
            "github": "testuser",
            "resume_config": {
                "education": ["Old Education"],
                "awards": ["Old Award"]
            }
        })

        # Then update
        response = client.put("/user-config", json={
            "consent": True,
            "user_email": "test@example.com",
            "github": "testuser",
            "resume_config": {
                "education": ["New Education"],
                "awards": ["New Award"]
            }
        })

        assert response.status_code == 200
        data = response.json()
        assert data["resume_config"]["education"] == ["New Education"]
        assert data["resume_config"]["awards"] == ["New Award"]

    def test_update_user_config_partial_resume_config_update(self, client):
        """Test that only provided fields in resume_config are updated"""
        # First create
        client.put("/user-config", json={
            "consent": True,
            "user_email": "test@example.com",
            "github": "testuser",
            "resume_config": {
                "education": ["Old Education"],
                "awards": ["Old Award"]
            }
        })

        # Update only education
        response = client.put("/user-config", json={
            "consent": True,
            "user_email": "test@example.com",
            "github": "testuser",
            "resume_config": {
                "education": ["New Education"]
            }
        })

        assert response.status_code == 200
        data = response.json()
        assert data["resume_config"]["education"] == ["New Education"]
        assert data["resume_config"]["awards"] == ["Old Award"]  # Unchanged

    def test_update_user_config_without_resume_config(self, client):
        """Test updating user config without providing resume_config"""
        response = client.put("/user-config", json={
            "consent": False,
            "user_email": "test@example.com",
            "github": "testuser"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["consent"] is False
        # resume_config should still exist (auto-created by CRUD)
        assert data["resume_config"] is not None

    def test_update_user_config_missing_required_fields(self, client):
        """Test that missing required fields returns 422"""
        response = client.put("/user-config", json={
            "consent": True
            # Missing user_email
        })

        assert response.status_code == 422

    def test_update_user_config_empty_body(self, client):
        """Test that empty body returns 422"""
        response = client.put("/user-config", json={})
        assert response.status_code == 422

    def test_update_user_config_with_multiple_education_entries(self, client):
        """Test updating with multiple education entries"""
        response = client.put("/user-config", json={
            "consent": True,
            "user_email": "test@example.com",
            "github": "testuser",
            "resume_config": {
                "education": [
                    "BSc Computer Science, UBC, 2024",
                    "High School Diploma, Some High School, 2020"
                ],
                "awards": [
                    "Dean's List 2023",
                    "Best Capstone Project Award"
                ]
            }
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["resume_config"]["education"]) == 2
        assert len(data["resume_config"]["awards"]) == 2


class TestGetUserConfigSafe:
    """Tests for get_user_config_safe helper function"""

    def test_get_user_config_safe_by_id(self, client):
        """Test that get_user_config_safe retrieves config by specific ID"""
        from src.interface.api.routers.user_config import get_user_config_safe
        from sqlmodel import Session

        mock_config = MagicMock(id=5)
        mock_session = MagicMock(spec=Session)
        mock_session.get.return_value = mock_config

        result = get_user_config_safe(mock_session, user_config_id=5)

        assert result.id == 5
        mock_session.get.assert_called_once()

    def test_get_user_config_safe_by_id_not_found(self, client):
        """Test that UserConfigNotFoundError is raised when specific ID doesn't exist"""
        from src.interface.api.routers.user_config import get_user_config_safe
        from src.utils.errors import UserConfigNotFoundError
        from sqlmodel import Session

        mock_session = MagicMock(spec=Session)
        mock_session.get.return_value = None

        with pytest.raises(UserConfigNotFoundError) as exc_info:
            get_user_config_safe(mock_session, user_config_id=999)

        assert "999" in str(exc_info.value)

    def test_get_user_config_safe_most_recent(self, client):
        """Test that get_user_config_safe returns most recent when no ID provided"""
        from src.interface.api.routers.user_config import get_user_config_safe
        from sqlmodel import Session

        mock_config = MagicMock(id=1)
        mock_session = MagicMock(spec=Session)

        with patch('src.interface.api.routers.user_config.get_most_recent_user_config') as mock_get:
            mock_get.return_value = mock_config

            result = get_user_config_safe(mock_session)

            assert result.id == 1
            mock_get.assert_called_once_with(mock_session)