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
        last_updated=datetime(2026, 2, 9, 10, 0, 0),
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
        weight_skills=weighted_skills,
        education=["BSc Computer Science"],
        awards=["Dean's List"]
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


# --- Tests for GET /resume/{resume_id} ---

def test_get_existing_resume(client, sample_resume_model):
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


def test_get_resume_with_dates(client, sample_resume_model):
    """Test that dates are properly serialized"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["start_date"] == "2025-01-01"
        assert data["items"][0]["end_date"] == "2025-12-31"


def test_get_nonexistent_resume(client):
    """Test retrieving a resume that doesn't exist"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = None

        response = client.get("/resume/999")

        assert response.status_code == 404
        assert "resume found" in response.json()["message"].lower()


def test_get_resume_with_null_fields(client, sample_resume_model):
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


def test_get_resume_invalid_id(client):
    """Test that non-integer ID returns validation error"""
    response = client.get("/resume/not-a-number")

    assert response.status_code == 422


# --- Tests for POST /resume/generate ---

def test_generate_resume_basic(client, sample_resume_domain, sample_resume_model):
    """Test basic resume generation"""
    mock_project = MagicMock()
    mock_project.project_name = "Test Project"

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_config, \
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


def test_generate_resume_empty_projects(client):
    """Test that empty project list returns 400"""
    response = client.post("/resume/generate", json={
        "project_names": []
    })

    assert response.status_code == 400
    assert "at least one project" in response.json()["detail"].lower()


def test_generate_resume_nonexistent_project(client):
    """Test that nonexistent project returns 404"""
    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get:
        mock_get.return_value = None

        response = client.post("/resume/generate", json={
            "project_names": ["NonexistentProject"]
        })

        assert response.status_code == 404
        assert "project found" in response.json()["message"].lower()


def test_generate_resume_with_user_config(client, sample_resume_domain, sample_resume_model):
    """Test generation with specific user config"""
    from src.database.api.models import UserConfigModel, ResumeConfigModel
    from src.interface.api.routers.util import get_session

    mock_project = MagicMock()
    mock_resume_config = ResumeConfigModel(
        id=1,
        user_config_id=1,
        education=["BSc CS, UBC, 2024"],
        awards=["Dean's List 2023"]
    )

    mock_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="config@example.com",
        github="configuser"
    )

    mock_config.resume_config = mock_resume_config

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
            patch('src.interface.api.routers.resume.save_resume') as mock_save, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_get_config:

        mock_get_project.return_value = mock_project
        mock_get_config.return_value = mock_config

        mock_report_instance = MagicMock()
        mock_report_instance.generate_resume.return_value = sample_resume_domain
        mock_user_report.return_value = mock_report_instance

        mock_save.return_value = sample_resume_model

        response = client.post("/resume/generate", json={
            "project_names": ["Test Project"],
            "user_config_id": 1
        })

        assert response.status_code == 200
        # Verify generate_resume was called with education/awards
        mock_report_instance.generate_resume.assert_called_once()
        call_kwargs = mock_report_instance.generate_resume.call_args.kwargs
        assert call_kwargs["education"] == ["BSc CS, UBC, 2024"]
        assert call_kwargs["awards"] == ["Dean's List 2023"]


def test_generate_resume_invalid_user_config(client):
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
            assert "user config" in response.json()["message"].lower()
        finally:
            client.app.dependency_overrides.pop(get_session, None)


def test_generate_resume_multiple_projects(client, sample_resume_domain, sample_resume_model):
    """Test generating resume from multiple projects"""
    mock_project = MagicMock()

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_config, \
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


def test_generate_resume_missing_field(client):
    """Test that missing required field returns validation error"""
    response = client.post("/resume/generate", json={})

    assert response.status_code == 422


def test_generate_resume_invalid_type(client):
    """Test that invalid type for project_names returns validation error"""
    response = client.post("/resume/generate", json={
        "project_names": "not-a-list"
    })

    assert response.status_code == 422


# --- Tests for POST /resume/{resume_id}/edit ---

def test_edit_resume_email(client, sample_resume_domain, sample_resume_model):
    """Test editing resume email"""
    sample_resume_model.email = "newemail@example.com"

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/metadata", json={
            "email": "newemail@example.com"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["email"] == "newemail@example.com"


def test_edit_nonexistent_resume(client):
    """Test editing a resume that doesn't exist"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = None

        response = client.post("/resume/999/edit/metadata", json={
            "email": "test@example.com"
        })

        assert response.status_code == 404
        assert "resume found" in response.json()["detail"].lower()


def test_edit_resume_null_email(client, sample_resume_domain, sample_resume_model):
    """Test editing resume with null email (no change)"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/metadata", json={
            "email": None
        })

        assert response.status_code == 200


def test_edit_resume_preserves_id(client, sample_resume_domain, sample_resume_model):
    """Test that resume ID is preserved after edit"""
    sample_resume_model.id = 1

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/metadata", json={
            "email": "test@example.com"
        })

        assert response.status_code == 200
        assert response.json()["id"] == 1


def test_edit_resume_empty_body(client, sample_resume_domain, sample_resume_model):
    """Test editing with empty request body"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/metadata", json={})

        assert response.status_code == 200


# --- Tests for error handling in resume endpoints ---

def test_generate_resume_save_failure(client, sample_resume_domain):
    """Test handling of save failure during generation"""
    mock_project = MagicMock()

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_config, \
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
        assert "failed to generate" in response.json()["message"].lower()


def test_edit_resume_save_failure(client, sample_resume_domain, sample_resume_model):
    """Test handling of save failure during edit"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        with patch('src.interface.api.routers.resume.datetime') as mock_dt:
            mock_dt.datetime.now.side_effect = Exception("Database error")

            response = client.post("/resume/1/edit/metadata", json={
                "email": "test@example.com"
            })

            assert response.status_code == 500
            assert "failed to edit" in response.json()["message"].lower()


# --- Tests for POST /resume/{resume_id}/edit/bullet_point ---

def test_append_bullet_point_success(client, sample_resume_model):
    """Test successfully appending a new bullet point"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        # Start with 2 bullet points
        assert len(sample_resume_model.items[0].bullet_points) == 2

        response = client.post("/resume/1/edit/bullet_point", json={
            "resume_id": 1,
            "item_index": 0,
            "new_content": "Appended Bullet",
            "append": True,
            "bullet_point_index": None
        })

        assert response.status_code == 200
        data = response.json()
        updated_bullets = data["items"][0]["bullet_points"]
        assert len(updated_bullets) == 3
        assert updated_bullets[-1] == "Appended Bullet"


def test_edit_existing_bullet_point_success(client, sample_resume_model):
    """Test successfully overwriting an existing bullet point"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/bullet_point", json={
            "resume_id": 1,
            "item_index": 0,
            "new_content": "Updated API",
            "append": False,
            "bullet_point_index": 0
        })

        assert response.status_code == 200
        data = response.json()
        updated_bullets = data["items"][0]["bullet_points"]
        assert len(updated_bullets) == 2
        assert updated_bullets[0] == "Updated API"


def test_edit_bullet_point_resume_not_found(client):
    """Test editing a bullet point on a non-existent resume"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = None

        response = client.post("/resume/999/edit/bullet_point", json={
            "resume_id": 999,
            "item_index": 0,
            "new_content": "Test",
            "append": True,
            "bullet_point_index": None
        })

        assert response.status_code == 404
        assert "no resume found" in response.json()["message"].lower()


def test_edit_bullet_point_invalid_item_index(client, sample_resume_model):
    """Test with an item_index out of bounds"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/bullet_point", json={
            "resume_id": 1,
            "item_index": 99,  # Out of bounds
            "new_content": "Test",
            "append": True,
            "bullet_point_index": None
        })

        assert response.status_code == 400
        assert "out of bounds" in response.json()["detail"].lower()


def test_edit_bullet_point_missing_bullet_index(client, sample_resume_model):
    """Test edit mode (append=False) without providing bullet_point_index"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/bullet_point", json={
            "resume_id": 1,
            "item_index": 0,
            "new_content": "Test",
            "append": False,
            "bullet_point_index": None  # Missing index
        })

        assert response.status_code == 400
        assert "must be provided if not appending" in response.json()[
            "detail"].lower()


def test_edit_bullet_point_invalid_bullet_index(client, sample_resume_model):
    """Test edit mode with a bullet_point_index out of bounds"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/bullet_point", json={
            "resume_id": 1,
            "item_index": 0,
            "new_content": "Test",
            "append": False,
            "bullet_point_index": 99  # Out of bounds
        })

        assert response.status_code == 400
        assert "invalid bullet_point_index" in response.json()[
            "detail"].lower()


def test_edit_bullet_point_db_failure(client, sample_resume_model):
    """Test database failure during bullet point edit"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.interface.api.routers.util.Session.commit') as mock_commit:
        # Assuming your get_session yields a standard Session

        mock_get.return_value = sample_resume_model
        mock_commit.side_effect = Exception("DB Timeout")

        # Need to patch the session inside the dependency or mock the add/commit directly
        # A simpler way since get_session is a dependency:
        client.app.dependency_overrides.pop(
            'src.interface.api.routers.util.get_session', None)

        with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get_override:
            mock_get_override.return_value = sample_resume_model

            # Mocking the commit failure directly on the router's session
            # This depends heavily on how `session` is scoped, but throwing an exception
            # inside the try block is the easiest way to test the 500 handler.

            with patch.object(sample_resume_model.items[0], 'bullet_points', side_effect=Exception("DB Error")):
                response = client.post("/resume/1/edit/bullet_point", json={
                    "resume_id": 1,
                    "item_index": 0,
                    "new_content": "DB Test",
                    "append": True,
                    "bullet_point_index": None
                })

                assert response.status_code == 500
                assert "failed to edit bullet point" in response.json()[
                    "message"].lower()


# --- Tests for POST /resume/{resume_id}/edit/resume_item ---

def test_edit_resume_item_success(client, sample_resume_model):
    """Test successfully editing resume item metadata"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/resume_item", json={
            "resume_id": 1,
            "item_index": 0,
            "title": "Senior Staff Engineer",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31"
        })

        assert response.status_code == 200
        data = response.json()
        item = data["items"][0]

        assert item["title"] == "Senior Staff Engineer"
        assert item["start_date"] == "2026-01-01"
        assert item["end_date"] == "2026-12-31"


def test_edit_resume_item_not_found(client):
    """Test editing metadata on a non-existent resume"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = None

        response = client.post("/resume/999/edit/resume_item", json={
            "resume_id": 999,
            "item_index": 0,
            "title": "Test",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31"
        })

        assert response.status_code == 404
        assert "no resume found" in response.json()["message"].lower()


def test_edit_resume_item_invalid_item_index(client, sample_resume_model):
    """Test metadata edit with an item_index out of bounds"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/resume_item", json={
            "resume_id": 1,
            "item_index": 99,  # Out of bounds
            "title": "Test",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31"
        })

        assert response.status_code == 400
        assert "out of bounds" in response.json()["detail"].lower()


def test_get_resume_with_education_and_awards(client, sample_resume_model):
    """Test retrieving resume includes education and awards"""
    sample_resume_model.education = [{"title": "BSc Computer Science", "start": None, "end": None}]
    sample_resume_model.awards = [{"title": "Dean's List", "start": None, "end": None}]

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()
        assert "education" in data
        assert "awards" in data
        assert len(data["education"]) == 1
        assert data["education"][0]["title"] == "BSc Computer Science"
        assert len(data["awards"]) == 1
        assert data["awards"][0]["title"] == "Dean's List"

def test_get_resume_with_empty_education_awards(client, sample_resume_model):
    """Test retrieving resume with empty education and awards lists"""
    from src.database.api.models import UserConfigModel, ResumeConfigModel

    # Mock user config with empty resume config
    mock_resume_config = ResumeConfigModel(
        id=1,
        user_config_id=1,
        education=[],
        awards=[]
    )
    mock_user_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="test@example.com",
        github="testuser"
    )
    mock_user_config.resume_config = mock_resume_config

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.database.get_most_recent_user_config') as mock_get_config:

        mock_get.return_value = sample_resume_model
        mock_get_config.return_value = mock_user_config

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()
        assert data["education"] == []
        assert data["awards"] == []


def test_generate_resume_with_user_config_no_resume_config(client, sample_resume_domain, sample_resume_model):
    """Test generation with user config that has no resume_config"""
    from src.database.api.models import UserConfigModel

    mock_project = MagicMock()
    mock_project.project_name = "Test Project"

    mock_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="config@example.com",
        github="configuser"
    )
    mock_config.resume_config = None

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
            patch('src.interface.api.routers.resume.save_resume') as mock_save, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_get_config:

        mock_get_project.return_value = mock_project
        mock_get_config.return_value = mock_config

        mock_report_instance = MagicMock()
        mock_report_instance.generate_resume.return_value = sample_resume_domain
        mock_user_report.return_value = mock_report_instance

        mock_save.return_value = sample_resume_model

        response = client.post("/resume/generate", json={
            "project_names": ["Test Project"],
            "user_config_id": 1
        })

        assert response.status_code == 200
        # Verify generate_resume was called with None for education/awards
        mock_report_instance.generate_resume.assert_called_once()
        call_kwargs = mock_report_instance.generate_resume.call_args.kwargs
        assert call_kwargs["education"] == []
        assert call_kwargs["awards"] == []


def test_generate_resume_with_empty_education_awards(client, sample_resume_domain, sample_resume_model):
    """Test generation with user config that has empty education/awards"""
    from src.database.api.models import UserConfigModel, ResumeConfigModel

    mock_project = MagicMock()

    mock_resume_config = ResumeConfigModel(
        id=1,
        user_config_id=1,
        education=[],
        awards=[]
    )

    mock_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="config@example.com",
        github="configuser"
    )
    mock_config.resume_config = mock_resume_config

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
            patch('src.interface.api.routers.resume.save_resume') as mock_save, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_get_config:

        mock_get_project.return_value = mock_project
        mock_get_config.return_value = mock_config

        mock_report_instance = MagicMock()
        mock_report_instance.generate_resume.return_value = sample_resume_domain
        mock_user_report.return_value = mock_report_instance

        mock_save.return_value = sample_resume_model

        response = client.post("/resume/generate", json={
            "project_names": ["Test Project"],
            "user_config_id": 1
        })

        assert response.status_code == 200
        call_kwargs = mock_report_instance.generate_resume.call_args.kwargs
        assert call_kwargs["education"] == []
        assert call_kwargs["awards"] == []


def test_refresh_resume_success(client, sample_resume_domain, sample_resume_model):
    """Test successfully refreshing a resume from its source projects"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get_model, \
            patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
            patch('src.interface.api.routers.resume.save_resume') as mock_save:

        # Mock the existing resume model with a project name
        mock_get_model.return_value = sample_resume_model

        # Mock project report
        mock_project = MagicMock()
        mock_project.project_name = "Test Project"
        mock_get_project.return_value = mock_project

        # Mock UserReport
        mock_report_instance = MagicMock()
        refreshed_resume = sample_resume_domain
        refreshed_resume.email = "refreshed@example.com"
        mock_report_instance.generate_resume.return_value = refreshed_resume
        mock_user_report.return_value = mock_report_instance

        # Mock save
        mock_save.return_value = sample_resume_model

        response = client.post("/resume/1/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1


def test_refresh_resume_not_found(client):
    """Test refreshing a non-existent resume"""
    with patch('src.interface.api.routers.resume.load_resume') as mock_load:
        mock_load.return_value = None

        response = client.post("/resume/999/refresh")

        assert response.status_code == 404
        assert "resume found" in response.json()["message"].lower()


def test_refresh_resume_no_items(client, sample_resume_model):
    """Test refreshing a resume with no items"""
    sample_resume_model.items = []

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get_model:
        mock_get_model.return_value = sample_resume_model

        response = client.post("/resume/1/refresh")

        assert response.status_code == 400
        assert "no projects" in response.json()["detail"].lower()


def test_refresh_resume_project_not_found(client, sample_resume_domain, sample_resume_model):
    """Test refreshing when source project no longer exists"""
    with patch('src.interface.api.routers.resume.load_resume') as mock_load, \
            patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get_model, \
            patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project:

        mock_load.return_value = sample_resume_domain
        mock_get_model.return_value = sample_resume_model
        mock_get_project.return_value = None

        response = client.post("/resume/1/refresh")

        assert response.status_code == 404
        assert "project" in response.json()["message"].lower()


def test_refresh_resume_preserves_manual_edits(client, sample_resume_domain, sample_resume_model):
    """Test that refreshing preserves the resume ID"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get_model, \
            patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
            patch('src.interface.api.routers.resume.save_resume') as mock_save:

        mock_get_model.return_value = sample_resume_model

        mock_project = MagicMock()
        mock_get_project.return_value = mock_project

        mock_report_instance = MagicMock()
        mock_report_instance.generate_resume.return_value = sample_resume_domain
        mock_user_report.return_value = mock_report_instance

        # Mock save to return model without ID
        sample_resume_model.id = None
        mock_save.return_value = sample_resume_model

        response = client.post("/resume/1/refresh")

        assert response.status_code == 200
        # Verify the ID was restored
        assert sample_resume_model.id == 1


# --- Tests for null start_date / end_date (wrong-email analysis bug) ---

def test_resume_item_allows_null_dates():
    """ResumeItem should accept None for start_date and end_date (project analyzed with wrong email)."""
    from src.core.resume.resume import ResumeItem

    item = ResumeItem(
        title="NullDateProject",
        frameworks=[],
        bullet_points=["Did some work"],
        start_date=None,
        end_date=None,
        project_name="NullDateProject",
    )

    assert item.start_date is None
    assert item.end_date is None


def test_serialize_resume_item_null_dates():
    """serialize_resume_item should produce a ResumeItemModel with null dates without raising."""
    from src.core.resume.resume import ResumeItem
    from src.database.core.model_serializer import serialize_resume_item

    item = ResumeItem(
        title="NullDateProject",
        frameworks=[],
        bullet_points=["Did some work"],
        start_date=None,
        end_date=None,
        project_name="NullDateProject",
    )

    model = serialize_resume_item(item)

    assert model.start_date is None
    assert model.end_date is None
    assert model.title == "NullDateProject"


def test_generate_resume_null_dates_succeeds(client, blank_db):
    """
    POST /resume/generate should succeed (200) even when the project was analyzed with
    the wrong email, causing start_date and end_date to be None on the resume items.

    Regression test for: NOT NULL constraint failed: resumeitemmodel.start_date
    """
    from src.core.resume.resume import Resume, ResumeItem
    from src.database.api.models import ResumeModel, ResumeItemModel
    from sqlmodel import Session

    # Build a resume domain object whose item has no dates (wrong-email scenario)
    resume_no_dates = Resume(email="wrong@example.com")
    null_date_item = ResumeItem(
        title="EarthLingo",
        frameworks=[],
        bullet_points=["Applied Web Dev to deliver project outcomes"],
        start_date=None,
        end_date=None,
        project_name="EarthLingo",
    )
    resume_no_dates.add_item(null_date_item)

    mock_project = MagicMock()
    mock_project.project_name = "EarthLingo"

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_config, \
            patch('src.interface.api.routers.resume.UserReport') as mock_user_report:

        mock_get_project.return_value = mock_project
        mock_config.return_value = None

        mock_report_instance = MagicMock()
        mock_report_instance.generate_resume.return_value = resume_no_dates
        mock_user_report.return_value = mock_report_instance

        response = client.post("/resume/generate", json={
            "project_names": ["EarthLingo"]
        })

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["start_date"] is None
    assert data["items"][0]["end_date"] is None


def test_resume_item_model_accepts_null_dates(blank_db):
    """ResumeItemModel should persist to DB with null start_date and end_date."""
    from src.database.api.models import ResumeModel, ResumeItemModel
    from sqlmodel import Session

    with Session(blank_db) as session:
        resume_model = ResumeModel(skills=[])
        session.add(resume_model)
        session.flush()

        item_model = ResumeItemModel(
            resume_id=resume_model.id,
            title="NullDateProject",
            frameworks=[],
            bullet_points=["Did some work"],
            start_date=None,
            end_date=None,
        )
        session.add(item_model)
        session.commit()
        session.refresh(item_model)

    assert item_model.start_date is None
    assert item_model.end_date is None