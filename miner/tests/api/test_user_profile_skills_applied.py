"""
Tests for user profile skills being automatically applied to resumes.

Covers:
- _apply_user_profile_skills helper (unit tests)
- generate_resume endpoint merging profile skills
- refresh_resume endpoint merging profile skills
"""
from unittest.mock import patch, MagicMock
from datetime import datetime, date
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bare_resume_model():
    """A ResumeModel with no detected skills."""
    from src.database.api.models import ResumeModel
    model = ResumeModel(
        id=1,
        email="user@example.com",
        github="userhandle",
        skills=[],
        skills_expert=[],
        skills_intermediate=[],
        skills_exposure=[],
        created_at=datetime(2026, 1, 1),
        last_updated=datetime(2026, 1, 1),
    )
    model.items = []
    return model


@pytest.fixture
def resume_model_with_detected(bare_resume_model):
    """A ResumeModel that already has skills from project-detection."""
    bare_resume_model.skills_expert = ["Python", "Docker"]
    bare_resume_model.skills_intermediate = ["React"]
    bare_resume_model.skills_exposure = ["Bash"]
    bare_resume_model.skills = ["Python", "Docker", "React", "Bash"]
    return bare_resume_model


@pytest.fixture
def user_config_with_skills():
    """A UserConfigModel whose ResumeConfigModel has profile skills."""
    from src.database.api.models import UserConfigModel, ResumeConfigModel
    config = UserConfigModel(
        id=1,
        consent=True,
        user_email="user@example.com",
        github="userhandle",
    )
    resume_cfg = ResumeConfigModel(
        id=1,
        user_config_id=1,
        skills=[
            "Python:Expert",
            "TensorFlow:Expert",
            "SQL:Intermediate",
            "Arduino:Exposure",
        ],
        education=[],
        awards=[],
    )
    config.resume_config = resume_cfg
    config.project_reports = []
    return config


@pytest.fixture
def user_config_no_skills():
    """A UserConfigModel with no profile skills."""
    from src.database.api.models import UserConfigModel, ResumeConfigModel
    config = UserConfigModel(id=1, consent=True, user_email="user@example.com")
    resume_cfg = ResumeConfigModel(id=1, user_config_id=1, skills=[], education=[], awards=[])
    config.resume_config = resume_cfg
    config.project_reports = []
    return config


# ---------------------------------------------------------------------------
# Unit tests for _apply_user_profile_skills
# ---------------------------------------------------------------------------

class TestApplyUserProfileSkills:
    """Unit tests for the _apply_user_profile_skills helper."""

    def _apply(self, model, raw_skills):
        from src.interface.api.routers.resume import _apply_user_profile_skills
        _apply_user_profile_skills(model, raw_skills)

    def test_parses_expert_level(self, bare_resume_model):
        self._apply(bare_resume_model, ["Python:Expert"])
        assert "Python" in bare_resume_model.skills_expert
        assert bare_resume_model.skills_intermediate == []
        assert bare_resume_model.skills_exposure == []

    def test_parses_intermediate_level(self, bare_resume_model):
        self._apply(bare_resume_model, ["SQL:Intermediate"])
        assert "SQL" in bare_resume_model.skills_intermediate

    def test_parses_exposure_level(self, bare_resume_model):
        self._apply(bare_resume_model, ["Arduino:Exposure"])
        assert "Arduino" in bare_resume_model.skills_exposure

    def test_unknown_level_falls_back_to_exposure(self, bare_resume_model):
        self._apply(bare_resume_model, ["Rust:Wizard"])
        assert "Rust" in bare_resume_model.skills_exposure

    def test_no_colon_falls_back_to_exposure(self, bare_resume_model):
        self._apply(bare_resume_model, ["Bash"])
        assert "Bash" in bare_resume_model.skills_exposure

    def test_flat_skills_list_updated(self, bare_resume_model):
        self._apply(bare_resume_model, ["Python:Expert", "SQL:Intermediate", "Bash:Exposure"])
        assert set(bare_resume_model.skills) == {"Python", "SQL", "Bash"}

    def test_profile_skill_overrides_detected_bucket(self, resume_model_with_detected):
        """Python is detected as Expert; profile lists it as Intermediate — profile wins."""
        self._apply(resume_model_with_detected, ["Python:Intermediate"])
        assert "Python" not in resume_model_with_detected.skills_expert
        assert "Python" in resume_model_with_detected.skills_intermediate

    def test_case_insensitive_deduplication(self, resume_model_with_detected):
        """Detected 'docker' and profile 'Docker:Expert' should not duplicate."""
        resume_model_with_detected.skills_intermediate = ["docker"]
        self._apply(resume_model_with_detected, ["Docker:Expert"])
        all_skills = (
            resume_model_with_detected.skills_expert
            + resume_model_with_detected.skills_intermediate
            + resume_model_with_detected.skills_exposure
        )
        docker_count = sum(1 for s in all_skills if s.lower() == "docker")
        assert docker_count == 1

    def test_detected_skills_not_in_profile_are_preserved(self, resume_model_with_detected):
        """React and Bash are detected but not in profile — they should survive."""
        self._apply(resume_model_with_detected, ["TensorFlow:Expert"])
        assert "React" in resume_model_with_detected.skills_intermediate
        assert "Bash" in resume_model_with_detected.skills_exposure

    def test_profile_skills_prepended_before_detected(self, resume_model_with_detected):
        """Profile skills should come first in each bucket."""
        self._apply(resume_model_with_detected, ["TensorFlow:Expert"])
        assert resume_model_with_detected.skills_expert[0] == "TensorFlow"

    def test_empty_profile_skills_leaves_model_unchanged(self, resume_model_with_detected):
        original_expert = list(resume_model_with_detected.skills_expert)
        self._apply(resume_model_with_detected, [])
        assert resume_model_with_detected.skills_expert == original_expert

    def test_multiple_profile_skills_all_added(self, bare_resume_model):
        self._apply(bare_resume_model, [
            "A:Expert", "B:Expert", "C:Intermediate", "D:Exposure"
        ])
        assert set(bare_resume_model.skills_expert) == {"A", "B"}
        assert set(bare_resume_model.skills_intermediate) == {"C"}
        assert set(bare_resume_model.skills_exposure) == {"D"}


# ---------------------------------------------------------------------------
# Integration tests: generate_resume applies profile skills
# ---------------------------------------------------------------------------

class TestGenerateResumeAppliesProfileSkills:

    def test_profile_skills_appear_in_generated_resume(
        self, client, bare_resume_model, user_config_with_skills
    ):
        """Profile skills (Python:Expert, TensorFlow:Expert, SQL:Intermediate, Arduino:Exposure)
        should all appear in the generated resume's skill buckets."""
        mock_domain = MagicMock()

        with patch("src.interface.api.routers.resume.get_project_report_by_name") as mock_proj, \
             patch("src.interface.api.routers.resume.get_user_config_safe") as mock_cfg, \
             patch("src.interface.api.routers.resume.UserReport") as mock_report_cls, \
             patch("src.interface.api.routers.resume.save_resume") as mock_save:

            mock_proj.return_value = MagicMock()
            mock_cfg.return_value = user_config_with_skills
            mock_report_cls.return_value.generate_resume.return_value = mock_domain
            mock_save.return_value = bare_resume_model

            response = client.post("/resume/generate", json={"project_names": ["proj1"]})

        assert response.status_code == 200
        data = response.json()
        expertise = data["skills_by_expertise"]
        assert expertise is not None
        assert "Python" in expertise["expert"]
        assert "TensorFlow" in expertise["expert"]
        assert "SQL" in expertise["intermediate"]
        assert "Arduino" in expertise["exposure"]

    def test_profile_skills_merged_with_detected(
        self, client, resume_model_with_detected, user_config_with_skills
    ):
        """Detected skills (React, Bash) not in profile should survive alongside profile skills."""
        mock_domain = MagicMock()

        with patch("src.interface.api.routers.resume.get_project_report_by_name") as mock_proj, \
             patch("src.interface.api.routers.resume.get_user_config_safe") as mock_cfg, \
             patch("src.interface.api.routers.resume.UserReport") as mock_report_cls, \
             patch("src.interface.api.routers.resume.save_resume") as mock_save:

            mock_proj.return_value = MagicMock()
            mock_cfg.return_value = user_config_with_skills
            mock_report_cls.return_value.generate_resume.return_value = mock_domain
            mock_save.return_value = resume_model_with_detected

            response = client.post("/resume/generate", json={"project_names": ["proj1"]})

        assert response.status_code == 200
        data = response.json()
        expertise = data["skills_by_expertise"]
        # Profile skills present
        assert "Python" in expertise["expert"]
        assert "TensorFlow" in expertise["expert"]
        assert "SQL" in expertise["intermediate"]
        # Detected skills that are NOT in profile are still there
        assert "React" in expertise["intermediate"]
        assert "Bash" in expertise["exposure"]

    def test_generate_without_profile_skills_unchanged(
        self, client, resume_model_with_detected, user_config_no_skills
    ):
        """When the user has no profile skills, detected skills are untouched."""
        mock_domain = MagicMock()

        with patch("src.interface.api.routers.resume.get_project_report_by_name") as mock_proj, \
             patch("src.interface.api.routers.resume.get_user_config_safe") as mock_cfg, \
             patch("src.interface.api.routers.resume.UserReport") as mock_report_cls, \
             patch("src.interface.api.routers.resume.save_resume") as mock_save:

            mock_proj.return_value = MagicMock()
            mock_cfg.return_value = user_config_no_skills
            mock_report_cls.return_value.generate_resume.return_value = mock_domain
            mock_save.return_value = resume_model_with_detected

            response = client.post("/resume/generate", json={"project_names": ["proj1"]})

        assert response.status_code == 200
        data = response.json()
        expertise = data["skills_by_expertise"]
        assert set(expertise["expert"]) == {"Python", "Docker"}
        assert set(expertise["intermediate"]) == {"React"}
        assert set(expertise["exposure"]) == {"Bash"}

    def test_profile_skill_level_overrides_detected_level(
        self, client, resume_model_with_detected, user_config_with_skills
    ):
        """Python is detected as Expert; profile says Expert too — only one Python in Expert."""
        mock_domain = MagicMock()

        with patch("src.interface.api.routers.resume.get_project_report_by_name") as mock_proj, \
             patch("src.interface.api.routers.resume.get_user_config_safe") as mock_cfg, \
             patch("src.interface.api.routers.resume.UserReport") as mock_report_cls, \
             patch("src.interface.api.routers.resume.save_resume") as mock_save:

            mock_proj.return_value = MagicMock()
            mock_cfg.return_value = user_config_with_skills
            mock_report_cls.return_value.generate_resume.return_value = mock_domain
            mock_save.return_value = resume_model_with_detected

            response = client.post("/resume/generate", json={"project_names": ["proj1"]})

        assert response.status_code == 200
        expertise = response.json()["skills_by_expertise"]
        assert expertise["expert"].count("Python") == 1


# ---------------------------------------------------------------------------
# Integration tests: refresh_resume applies profile skills
# ---------------------------------------------------------------------------

class TestRefreshResumeAppliesProfileSkills:

    def _make_refresh_model(self, skills_expert=None, skills_intermediate=None, skills_exposure=None):
        """Build a real ResumeModel suitable for use as a save_resume return value."""
        from src.database.api.models import ResumeModel
        model = ResumeModel(
            id=1,
            email="user@example.com",
            github="userhandle",
            skills=(skills_expert or []) + (skills_intermediate or []) + (skills_exposure or []),
            skills_expert=skills_expert or [],
            skills_intermediate=skills_intermediate or [],
            skills_exposure=skills_exposure or [],
            created_at=datetime(2026, 1, 1),
            last_updated=datetime(2026, 1, 1),
        )
        model.items = []
        return model

    def test_profile_skills_appear_after_refresh(
        self, client, bare_resume_model, user_config_with_skills
    ):
        """After refresh, profile skills should be merged into the updated model."""
        from src.database.api.models import ResumeItemModel

        item = ResumeItemModel(
            id=1, resume_id=1, project_name="proj1",
            title="Dev", frameworks=[], bullet_points=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
        )
        bare_resume_model.items = [item]
        refreshed_model = self._make_refresh_model()
        mock_domain = MagicMock()

        with patch("src.interface.api.routers.resume.get_resume_model_by_id") as mock_get, \
             patch("src.interface.api.routers.resume.get_project_report_by_name") as mock_proj, \
             patch("src.interface.api.routers.resume.UserReport") as mock_report_cls, \
             patch("src.interface.api.routers.resume.save_resume") as mock_save, \
             patch("src.database.get_most_recent_user_config") as mock_user_cfg:

            mock_get.return_value = bare_resume_model
            mock_proj.return_value = MagicMock()
            mock_report_cls.return_value.generate_resume.return_value = mock_domain
            mock_save.return_value = refreshed_model
            mock_user_cfg.return_value = user_config_with_skills

            response = client.post("/resume/1/refresh")

        assert response.status_code == 200
        expertise = response.json()["skills_by_expertise"]
        assert expertise is not None
        assert "Python" in expertise["expert"]
        assert "TensorFlow" in expertise["expert"]
        assert "SQL" in expertise["intermediate"]
        assert "Arduino" in expertise["exposure"]

    def test_refresh_without_profile_skills_leaves_detected_intact(
        self, client, resume_model_with_detected, user_config_no_skills
    ):
        """Refresh with empty profile skills should not alter detected skills."""
        from src.database.api.models import ResumeItemModel

        item = ResumeItemModel(
            id=1, resume_id=1, project_name="proj1",
            title="Dev", frameworks=[], bullet_points=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
        )
        resume_model_with_detected.items = [item]
        refreshed_model = self._make_refresh_model(
            skills_expert=["Python", "Docker"],
            skills_intermediate=["React"],
            skills_exposure=["Bash"],
        )
        mock_domain = MagicMock()

        with patch("src.interface.api.routers.resume.get_resume_model_by_id") as mock_get, \
             patch("src.interface.api.routers.resume.get_project_report_by_name") as mock_proj, \
             patch("src.interface.api.routers.resume.UserReport") as mock_report_cls, \
             patch("src.interface.api.routers.resume.save_resume") as mock_save, \
             patch("src.database.get_most_recent_user_config") as mock_user_cfg:

            mock_get.return_value = resume_model_with_detected
            mock_proj.return_value = MagicMock()
            mock_report_cls.return_value.generate_resume.return_value = mock_domain
            mock_save.return_value = refreshed_model
            mock_user_cfg.return_value = user_config_no_skills

            response = client.post("/resume/1/refresh")

        assert response.status_code == 200
        expertise = response.json()["skills_by_expertise"]
        assert set(expertise["expert"]) == {"Python", "Docker"}
        assert set(expertise["intermediate"]) == {"React"}
        assert set(expertise["exposure"]) == {"Bash"}
