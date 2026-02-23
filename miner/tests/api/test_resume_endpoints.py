"""
Tests for the resume API endpoints.
"""

import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_resume_model():
    """Create a sample ResumeModel for testing"""
    from src.database.api.models import ResumeModel, ResumeItemModel

    resume = ResumeModel(
        id=1,
        email="test@example.com",
        github="testuser",
        skills=["Python", "JavaScript", "SQL"],
        created_at=datetime(2026, 2, 9, 10, 0, 0),
        last_updated=datetime(2026, 2, 9, 10, 0, 0)
    )

    item = ResumeItemModel(
        id=1,
        resume_id=1,
        project_name="Test Project",
        title="Software Engineer",
        frameworks=["FastAPI", "React"],
        bullet_points=["Built API", "Designed UI"],
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31)
    )

    resume.items = [item]
    return resume


@pytest.fixture
def sample_resume_domain():
    """Create a sample Resume domain object"""
    from src.core.resume.resume import Resume, ResumeItem
    from src.core.statistic import WeightedSkills

    # Create weighted skills for the resume
    weighted_skills = [
        WeightedSkills("Python", 0.9),
        WeightedSkills("JavaScript", 0.8),
        WeightedSkills("SQL", 0.7)
    ]

    # Create resume with email and weighted_skills
    resume = Resume(
        email="test@example.com",
        weight_skills=weighted_skills
    )

    # Manually set github since it's not in __init__
    resume.github = "testuser"

    # Create and add item
    item = ResumeItem(
        title="Software Engineer",
        frameworks=[WeightedSkills("FastAPI", 1.0),
                    WeightedSkills("React", 0.9)],
        bullet_points=["Built API", "Designed UI"],
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31)
    )

    resume.add_item(item)

    return resume


class TestGetResume:
    """Tests for GET /resume/{resume_id}"""

    def test_get_existing_resume(self, client, sample_resume_model):
        """Test retrieving an existing resume"""
        with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
            mock_get.return_value = sample_resume_model

            response = client.get("/resume/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["email"] == "test@example.com"
            assert data["github"] == "testuser"
            assert len(data["skills"]) == 3
            assert len(data["items"]) == 1
            assert data["items"][0]["title"] == "Software Engineer"

    def test_get_resume_with_dates(self, client, sample_resume_model):
        """Test that dates are properly serialized"""
        with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
            mock_get.return_value = sample_resume_model

            response = client.get("/resume/1")

            assert response.status_code == 200
            data = response.json()
            assert data["items"][0]["start_date"] == "2025-01-01"
            assert data["items"][0]["end_date"] == "2025-12-31"

    def test_get_nonexistent_resume(self, client):
        """Test retrieving a resume that doesn't exist"""
        with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
            mock_get.return_value = None

            response = client.get("/resume/999")

            assert response.status_code == 404
            assert "resume found" in response.json()["detail"].lower()

    def test_get_resume_with_null_fields(self, client, sample_resume_model):
        """Test retrieving resume with null email and github"""
        sample_resume_model.email = None
        sample_resume_model.github = None

        with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
            mock_get.return_value = sample_resume_model

            response = client.get("/resume/1")

            assert response.status_code == 200
            data = response.json()
            assert data["email"] is None
            assert data["github"] is None

    def test_get_resume_invalid_id(self, client):
        """Test that non-integer ID returns validation error"""
        response = client.get("/resume/not-a-number")

        assert response.status_code == 422


class TestGenerateResume:
    """Tests for POST /resume/generate"""

    def test_generate_resume_basic(self, client, sample_resume_domain, sample_resume_model):
        """Test basic resume generation"""
        mock_project = MagicMock()
        mock_project.project_name = "Test Project"

        with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
                patch('src.interface.api.routers.resume.get_most_recent_user_config') as mock_config, \
                patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_get_project.return_value = mock_project
            mock_config.return_value = None

            mock_report_instance = MagicMock()
            mock_report_instance.generate_resume.return_value = sample_resume_domain
            mock_user_report.return_value = mock_report_instance

            mock_save.return_value = sample_resume_model

            response = client.post("/resume/generate", json={
                "project_names": ["Test Project"]
            })

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["email"] == "test@example.com"

    def test_generate_resume_empty_projects(self, client):
        """Test that empty project list returns 400"""
        response = client.post("/resume/generate", json={
            "project_names": []
        })

        assert response.status_code == 400
        assert "at least one project" in response.json()["detail"].lower()

    def test_generate_resume_nonexistent_project(self, client):
        """Test that nonexistent project returns 404"""
        with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get:
            mock_get.return_value = None

            response = client.post("/resume/generate", json={
                "project_names": ["NonexistentProject"]
            })

            assert response.status_code == 404
            assert "project found" in response.json()["detail"].lower()

    def test_generate_resume_with_user_config(self, client, sample_resume_domain, sample_resume_model):
        """Test generation with specific user config"""
        from src.database.api.models import UserConfigModel
        from src.interface.api.routers.util import get_session


        mock_project = MagicMock()
        mock_config = UserConfigModel(
            id=1,
            user_email="config@example.com",
            github="configuser"
        )

        with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
                patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_get_project.return_value = mock_project

            mock_report_instance = MagicMock()
            mock_report_instance.generate_resume.return_value = sample_resume_domain
            mock_user_report.return_value = mock_report_instance

            mock_save.return_value = sample_resume_model

            # Mock the session.get call

            mock_session = MagicMock()
            mock_session.get.return_value = mock_config
            mock_session.commit = MagicMock()

            def _fake_get_session():
                yield mock_session

            client.app.dependency_overrides[get_session] = _fake_get_session

            try:
                response = client.post("/resume/generate", json={
                    "project_names": ["Test Project"],
                    "user_config_id": 1
                })
                assert response.status_code == 200
            finally:
                client.app.dependency_overrides.pop(get_session, None)

    def test_generate_resume_invalid_user_config(self, client):
        """Test that invalid user_config_id returns 404"""
        from src.interface.api.routers.util import get_session

        mock_project = MagicMock()

        with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project:
            mock_get_project.return_value = mock_project

            mock_session = MagicMock()
            mock_session.get.return_value = None

            def _fake_get_session_none():
                yield mock_session

            client.app.dependency_overrides[get_session] = _fake_get_session_none

            try:
                response = client.post("/resume/generate", json={
                    "project_names": ["Test Project"],
                    "user_config_id": 999
                })
                assert response.status_code == 404
                assert "user config" in response.json()["detail"].lower()
            finally:
                client.app.dependency_overrides.pop(get_session, None)


    def test_generate_resume_multiple_projects(self, client, sample_resume_domain, sample_resume_model):
        """Test generating resume from multiple projects"""
        mock_project = MagicMock()

        with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
                patch('src.interface.api.routers.resume.get_most_recent_user_config') as mock_config, \
                patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_get_project.return_value = mock_project
            mock_config.return_value = None

            mock_report_instance = MagicMock()
            mock_report_instance.generate_resume.return_value = sample_resume_domain
            mock_user_report.return_value = mock_report_instance

            mock_save.return_value = sample_resume_model

            response = client.post("/resume/generate", json={
                "project_names": ["Project1", "Project2", "Project3"]
            })

            assert response.status_code == 200
            assert mock_get_project.call_count == 3

    def test_generate_resume_missing_field(self, client):
        """Test that missing required field returns validation error"""
        response = client.post("/resume/generate", json={})

        assert response.status_code == 422

    def test_generate_resume_invalid_type(self, client):
        """Test that invalid type for project_names returns validation error"""
        response = client.post("/resume/generate", json={
            "project_names": "not-a-list"
        })

        assert response.status_code == 422


class TestEditResume:
    """Tests for POST /resume/{resume_id}/edit"""

    def test_edit_resume_email(self, client, sample_resume_domain, sample_resume_model):
        """Test editing resume email"""
        sample_resume_model.email = "newemail@example.com"

        with patch('src.interface.api.routers.resume.load_resume') as mock_load, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_load.return_value = sample_resume_domain
            mock_save.return_value = sample_resume_model

            response = client.post("/resume/1/edit", json={
                "email": "newemail@example.com"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["email"] == "newemail@example.com"
            assert sample_resume_domain.email == "newemail@example.com"

    def test_edit_nonexistent_resume(self, client):
        """Test editing a resume that doesn't exist"""
        with patch('src.interface.api.routers.resume.load_resume') as mock_load:
            mock_load.return_value = None

            response = client.post("/resume/999/edit", json={
                "email": "test@example.com"
            })

            assert response.status_code == 404
            assert "resume found" in response.json()["detail"].lower()

    def test_edit_resume_null_email(self, client, sample_resume_domain, sample_resume_model):
        """Test editing resume with null email (no change)"""
        with patch('src.interface.api.routers.resume.load_resume') as mock_load, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_load.return_value = sample_resume_domain
            mock_save.return_value = sample_resume_model

            response = client.post("/resume/1/edit", json={
                "email": None
            })

            assert response.status_code == 200

    def test_edit_resume_preserves_id(self, client, sample_resume_domain, sample_resume_model):
        """Test that resume ID is preserved after edit"""
        sample_resume_model.id = None  # Simulate save_resume returning model without ID

        with patch('src.interface.api.routers.resume.load_resume') as mock_load, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_load.return_value = sample_resume_domain
            mock_save.return_value = sample_resume_model

            response = client.post("/resume/1/edit", json={
                "email": "test@example.com"
            })

            assert response.status_code == 200
            assert sample_resume_model.id == 1

    def test_edit_resume_invalid_id(self, client):
        """Test that non-integer ID returns validation error"""
        response = client.post("/resume/not-a-number/edit", json={
            "email": "test@example.com"
        })

        assert response.status_code == 422

    def test_edit_resume_empty_body(self, client, sample_resume_domain, sample_resume_model):
        """Test editing with empty request body"""
        with patch('src.interface.api.routers.resume.load_resume') as mock_load, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_load.return_value = sample_resume_domain
            mock_save.return_value = sample_resume_model

            response = client.post("/resume/1/edit", json={})

            assert response.status_code == 200


class TestResumeErrorHandling:
    """Tests for error handling in resume endpoints"""

    def test_generate_resume_save_failure(self, client, sample_resume_domain):
        """Test handling of save failure during generation"""
        mock_project = MagicMock()

        with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
                patch('src.interface.api.routers.resume.get_most_recent_user_config') as mock_config, \
                patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_get_project.return_value = mock_project
            mock_config.return_value = None

            mock_report_instance = MagicMock()
            mock_report_instance.generate_resume.return_value = sample_resume_domain
            mock_user_report.return_value = mock_report_instance

            mock_save.side_effect = Exception("Database error")

            response = client.post("/resume/generate", json={
                "project_names": ["Test Project"]
            })

            assert response.status_code == 500
            assert "failed to generate" in response.json()["detail"].lower()

    def test_edit_resume_save_failure(self, client, sample_resume_domain):
        """Test handling of save failure during edit"""
        with patch('src.interface.api.routers.resume.load_resume') as mock_load, \
                patch('src.interface.api.routers.resume.save_resume') as mock_save:

            mock_load.return_value = sample_resume_domain
            mock_save.side_effect = Exception("Database error")

            response = client.post("/resume/1/edit", json={
                "email": "test@example.com"
            })

            assert response.status_code == 500
            assert "failed to edit" in response.json()["detail"].lower()
