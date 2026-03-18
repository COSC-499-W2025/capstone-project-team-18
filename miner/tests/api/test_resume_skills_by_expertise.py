"""
Tests for resume skills categorization by expertise level.
"""
from datetime import datetime, date
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def sample_resume_model():
    """Create a sample ResumeModel for testing"""
    from src.database.api.models import ResumeModel, ResumeItemModel

    resume = ResumeModel(
        id=1,
        email="test@example.com",
        github="testuser",
        skills=["Python", "JavaScript", "SQL"],
        skills_expert=[],  # Start empty, tests will set manually
        skills_intermediate=[],
        skills_exposure=[],
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



def test_get_resume_with_skills_by_expertise(client, sample_resume_model):
    """Test that resume includes skills categorized by expertise level"""
    from src.database.api.models import UserConfigModel, ProjectReportModel
    from src.core.statistic import WeightedSkills

    mock_user_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="test@example.com",
        github="testuser"
    )

    mock_project = ProjectReportModel(
        project_name="Test Project",
        user_config_used=1,
        statistic={}
    )
    mock_user_config.project_reports = [mock_project]

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.database.get_most_recent_user_config') as mock_get_config, \
            patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_load_project, \
            patch('src.core.report.user.user_report.UserReport') as mock_user_report:

        mock_get.return_value = sample_resume_model
        mock_get_config.return_value = mock_user_config
        mock_load_project.return_value = MagicMock()

        mock_report_instance = MagicMock()
        mock_stats = MagicMock()

        mock_report_instance = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get_value.return_value = [
            WeightedSkills("Docker", 0.85),
            WeightedSkills("Python", 0.75),
            WeightedSkills("React", 0.55),
            WeightedSkills("AWS", 0.45),
            WeightedSkills("Rust", 0.25),
        ]
        mock_report_instance.statistics = mock_stats
        mock_user_report.return_value = mock_report_instance

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()

        assert "skills_by_expertise" in data
        assert data["skills_by_expertise"] is not None

        expertise = data["skills_by_expertise"]
        assert "Docker" in expertise["expert"]
        assert "Python" in expertise["expert"]
        assert "React" in expertise["intermediate"]
        assert "AWS" in expertise["intermediate"]
        assert "Rust" in expertise["exposure"]


def test_get_resume_with_no_skills(client, sample_resume_model):
    """Test resume with no weighted skills returns null skills_by_expertise"""
    from src.database.api.models import UserConfigModel

    mock_user_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="test@example.com",
        github="testuser"
    )
    mock_user_config.project_reports = []  # No projects

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.database.get_most_recent_user_config') as mock_get_config:

        mock_get.return_value = sample_resume_model
        mock_get_config.return_value = mock_user_config

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()

        assert data["skills_by_expertise"] is None


def test_get_resume_with_only_expert_skills(client, sample_resume_model):
    """Test resume with only high-weight skills (all expert)"""
    from src.database.api.models import UserConfigModel, ProjectReportModel
    from src.core.statistic import WeightedSkills

    mock_user_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="test@example.com",
        github="testuser"
    )

    mock_project = ProjectReportModel(
        project_name="Test Project",
        user_config_used=1,
        statistic={}
    )
    mock_user_config.project_reports = [mock_project]

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.database.get_most_recent_user_config') as mock_get_config, \
            patch('src.database.api.CRUD.projects.get_project_report_model_by_name') as mock_load_project, \
            patch('src.core.report.user.user_report.UserReport') as mock_user_report:

        mock_get.return_value = sample_resume_model
        mock_get_config.return_value = mock_user_config
        mock_load_project.return_value = MagicMock()

        mock_report_instance = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get_value.return_value = [
            WeightedSkills("Python", 0.95),
            WeightedSkills("Docker", 0.85),
            WeightedSkills("Kubernetes", 0.75),
        ]
        mock_report_instance.statistics = mock_stats
        mock_user_report.return_value = mock_report_instance

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()

        expertise = data["skills_by_expertise"]
        assert len(expertise["expert"]) == 3
        assert len(expertise["intermediate"]) == 0
        assert len(expertise["exposure"]) == 0


def test_get_resume_with_threshold_boundary_skills(client, sample_resume_model):
    """Test skills at exact threshold boundaries (0.7, 0.4)"""
    from src.database.api.models import UserConfigModel, ProjectReportModel
    from src.core.statistic import WeightedSkills

    mock_user_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="test@example.com",
        github="testuser"
    )

    mock_project = ProjectReportModel(
        project_name="Test Project",
        user_config_used=1,
        statistic={}
    )
    mock_user_config.project_reports = [mock_project]

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.database.get_most_recent_user_config') as mock_get_config, \
            patch('src.database.api.CRUD.projects.get_project_report_model_by_name') as mock_load_project, \
            patch('src.core.report.user.user_report.UserReport') as mock_user_report:

        mock_get.return_value = sample_resume_model
        mock_get_config.return_value = mock_user_config
        mock_load_project.return_value = MagicMock()

        mock_report_instance = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get_value.return_value = [
            WeightedSkills("Skill1", 0.7),
            WeightedSkills("Skill2", 0.69),
            WeightedSkills("Skill3", 0.4),
            WeightedSkills("Skill4", 0.39),
        ]
        mock_report_instance.statistics = mock_stats
        mock_user_report.return_value = mock_report_instance

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()

        expertise = data["skills_by_expertise"]
        assert "Skill1" in expertise["expert"]
        assert "Skill2" in expertise["intermediate"]
        assert "Skill3" in expertise["intermediate"]
        assert "Skill4" in expertise["exposure"]

def test_get_resume_skills_by_expertise_no_user_config(client, sample_resume_model):
    """Test that resume returns null skills_by_expertise when no user config exists"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.database.get_most_recent_user_config') as mock_get_config:

        mock_get.return_value = sample_resume_model
        mock_get_config.return_value = None  # No user config

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()
        assert data["skills_by_expertise"] is None

def test_edit_resume_skills_success(client, sample_resume_model):
    """Test successfully editing categorized skills"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/skills", json={
            "expert": ["Python", "Docker"],
            "intermediate": ["React", "AWS"],
            "exposure": ["Rust", "Kubernetes"]
        })

        assert response.status_code == 200
        data = response.json()

        # Verify skills were updated
        expertise = data["skills_by_expertise"]
        assert set(expertise["expert"]) == {"Python", "Docker"}
        assert set(expertise["intermediate"]) == {"React", "AWS"}
        assert set(expertise["exposure"]) == {"Rust", "Kubernetes"}

        # Verify flat skills list was updated
        assert set(data["skills"]) == {"Python", "Docker", "React", "AWS", "Rust", "Kubernetes"}


def test_edit_resume_skills_not_found(client):
    """Test editing skills on non-existent resume"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = None

        response = client.post("/resume/999/edit/skills", json={
            "expert": ["Python"],
            "intermediate": [],
            "exposure": []
        })

        assert response.status_code == 404
        assert "resume found" in response.json()["detail"].lower()


def test_edit_resume_skills_empty_lists(client, sample_resume_model):
    """Test editing with empty skill lists"""
    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get:
        mock_get.return_value = sample_resume_model

        response = client.post("/resume/1/edit/skills", json={
            "expert": [],
            "intermediate": [],
            "exposure": []
        })

        assert response.status_code == 200
        data = response.json()
        assert data["skills_by_expertise"]["expert"] == []
        assert data["skills"] == []


def test_edit_resume_skills_validation_error(client):
    """Test that invalid request returns 422"""
    response = client.post("/resume/1/edit/skills", json={
        "expert": ["Python"]
        # Missing intermediate and exposure
    })

    assert response.status_code == 422


def test_get_resume_prefers_stored_skills(client, sample_resume_model):
    """Test that GET /resume/{id} returns stored skills over calculated ones"""
    from src.database.api.models import UserConfigModel

    # Set manually edited skills on resume
    sample_resume_model.skills_expert = ["Manually Set Expert Skill"]
    sample_resume_model.skills_intermediate = ["Manually Set Intermediate"]
    sample_resume_model.skills_exposure = []

    mock_user_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="test@example.com",
        github="testuser"
    )
    mock_user_config.project_reports = []

    with patch('src.interface.api.routers.resume.get_resume_model_by_id') as mock_get, \
            patch('src.database.get_most_recent_user_config') as mock_get_config:

        mock_get.return_value = sample_resume_model
        mock_get_config.return_value = mock_user_config

        response = client.get("/resume/1")

        assert response.status_code == 200
        data = response.json()

        # Should return manually edited skills, NOT calculated ones
        assert data["skills_by_expertise"]["expert"] == ["Manually Set Expert Skill"]
        assert data["skills_by_expertise"]["intermediate"] == ["Manually Set Intermediate"]


def test_generate_resume_snapshots_skills(client, sample_resume_domain, sample_resume_model):
    """Test that newly generated resume snapshots skills at generation time"""
    from src.database.api.models import UserConfigModel, ProjectReportModel
    from src.core.statistic import WeightedSkills

    mock_project = MagicMock()
    mock_user_config = UserConfigModel(
        id=1,
        consent=True,
        user_email="test@example.com",
        github="testuser"
    )

    # Set up resume model with snapshotted skills
    sample_resume_model.skills_expert = ["Python", "Docker"]
    sample_resume_model.skills_intermediate = ["React"]
    sample_resume_model.skills_exposure = ["Rust"]

    with patch('src.interface.api.routers.resume.get_project_report_by_name') as mock_get_project, \
            patch('src.interface.api.routers.resume.get_user_config_safe') as mock_get_config, \
            patch('src.interface.api.routers.resume.UserReport') as mock_user_report, \
            patch('src.interface.api.routers.resume.save_resume') as mock_save, \
            patch('src.database.get_most_recent_user_config') as mock_get_recent_config:

        mock_get_project.return_value = mock_project
        mock_get_config.return_value = mock_user_config
        mock_get_recent_config.return_value = mock_user_config