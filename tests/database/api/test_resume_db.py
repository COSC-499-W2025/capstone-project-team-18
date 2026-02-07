"""
Tests CRUD for the Resume object
"""

from datetime import date
import pytest
from sqlmodel import Session

from src.core.resume.resume import Resume, ResumeItem
from src.core.statistic import WeightedSkills
from src.database.api.CRUD.resume import save_resume, load_resume


def create_sample_resume() -> Resume:
    resume = Resume(
        email="test@example.com",
        github="github.com/test",
        weight_skills=[
            WeightedSkills("Python", 10),
            WeightedSkills("React", 8),
            WeightedSkills("SQL", 6),
        ],
    )

    item = ResumeItem(
        title="Test Project",
        frameworks=[
            WeightedSkills("Python", 10),
            WeightedSkills("FastAPI", 7),
            WeightedSkills("SQLModel", 6),
        ],
        bullet_points=[
            "Built an API",
            "Implemented database models",
        ],
        start_date=date(2023, 1, 1),
        end_date=date(2023, 6, 1),
    )

    resume.add_item(item)
    return resume


def test_save_and_load_resume(temp_db):
    resume = create_sample_resume()

    with Session(temp_db) as session:
        saved_model = save_resume(session, resume)

        assert saved_model.id is not None
        assert saved_model.email == "test@example.com"
        assert saved_model.github == "github.com/test"
        assert len(saved_model.items) == 1

        loaded_resume = load_resume(session, saved_model.id)

        assert loaded_resume is not None
        assert loaded_resume.email == "test@example.com"
        assert loaded_resume.github == "github.com/test"
        assert len(loaded_resume.items) == 1


def test_resume_item_fields_preserved(temp_db):
    resume = create_sample_resume()

    with Session(temp_db) as session:
        saved_model = save_resume(session, resume)

        if saved_model is None or saved_model.id is None:
            pytest.fail()

        loaded_resume = load_resume(session, saved_model.id)

        item = loaded_resume.items[0]  # pyright: ignore

        assert item.title == "Test Project"
        assert item.bullet_points == [
            "Built an API",
            "Implemented database models",
        ]

        assert item.start_date == date(2023, 1, 1)
        assert item.end_date == date(2023, 6, 1)

        framework_names = [fw.skill_name for fw in item.frameworks]
        assert framework_names == ["Python", "FastAPI", "SQLModel"]


def test_load_nonexistent_resume_returns_none(temp_db):
    with Session(temp_db) as session:
        resume = load_resume(session, 9999)
        assert resume is None


def test_resume_with_multiple_items(temp_db):
    resume = Resume(email="multi@test.com")

    for i in range(3):
        resume.add_item(
            ResumeItem(
                title=f"Project {i}",
                frameworks=[WeightedSkills("Python", 5)],
                bullet_points=[f"Did thing {i}"],
                start_date=date(2022, 1, 1),
                end_date=date(2022, 6, 1),
            )
        )

    with Session(temp_db) as session:
        saved_model = save_resume(session, resume)
        loaded_resume = load_resume(session, saved_model.id)  # pyright: ignore

        assert loaded_resume is not None
        assert len(loaded_resume.items) == 3
        titles = [item.title for item in loaded_resume.items]
        assert titles == ["Project 0", "Project 1", "Project 2"]
