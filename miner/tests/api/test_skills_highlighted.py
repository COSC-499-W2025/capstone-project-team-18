import datetime
import importlib

from sqlmodel import Session

from src.database.api.models import ProjectReportModel
from src.core.statistic.statistic_models import WeightedSkills

skills_router = importlib.import_module("src.interface.api.routers.skills")


def _insert_project(engine, project_name: str, highlight_skills: list[str] | None = None) -> None:
    """
    Insert a minimal ProjectReportModel row that satisfies NOT NULL constraints.
    """
    with Session(engine) as session:
        now = datetime.datetime.now()
        model = ProjectReportModel(
            project_name=project_name,
            user_config_used=None,
            image_data=None,
            statistic={"dummy": True},
            created_at=now,
            last_updated=now,
            analyzed_count=1,
            parent=None,

            # representation fields
            representation_rank=None,
            chrono_start_override=None,
            chrono_end_override=None,
            showcase_selected=False,
            compare_attributes=[],
            highlight_skills=list(highlight_skills or []),
            representation_last_user_edit_at=None,

            # showcase override fields
            showcase_title=None,
            showcase_start_date=None,
            showcase_end_date=None,
            showcase_frameworks=[],
            showcase_bullet_points=[],
            showcase_last_user_edit_at=None,
        )
        session.add(model)
        session.commit()


def test_get_highlighted_skills_returns_weights_and_defaults(client, blank_db, monkeypatch):
    """
    - Insert projects with highlight_skills
    - Monkeypatch get_skills(session) to return deterministic weights
    - Verify endpoint returns highlighted skills with correct weights
      (and 0.0 for missing)
    """
    _insert_project(blank_db, "P1", ["Python", "React"])
    _insert_project(blank_db, "P2", ["FastAPI"])

    def fake_get_skills(_session):
        return [
            WeightedSkills(skill_name="Python", weight=0.6),
            WeightedSkills(skill_name="FastAPI", weight=0.9),
        ]

    monkeypatch.setattr(skills_router, "get_skills", fake_get_skills)

    r = client.get("/skills/highlighted")
    assert r.status_code == 200, r.text

    body = r.json()
    out = body["skills"]

    # endpoint sorts highlighted names
    names = [x["name"] for x in out]
    assert names == ["FastAPI", "Python", "React"]

    weights = {x["name"]: x["weight"] for x in out}
    assert weights["FastAPI"] == 0.9
    assert weights["Python"] == 0.6
    assert weights["React"] == 0.0


def test_get_highlighted_skills_empty_when_none_selected(client, blank_db, monkeypatch):
    """
    If no project has highlight_skills, endpoint should return empty list.
    """
    _insert_project(blank_db, "P1", [])
    _insert_project(blank_db, "P2", None)

    def fake_get_skills(_session):
        return [WeightedSkills(skill_name="Python", weight=1.0)]

    monkeypatch.setattr(skills_router, "get_skills", fake_get_skills)

    r = client.get("/skills/highlighted")
    assert r.status_code == 200, r.text
    assert r.json()["skills"] == []

def test_get_highlighted_skills_dedupes_across_projects(client, blank_db, monkeypatch):
    _insert_project(blank_db, "P1", ["Python", "React"])
    _insert_project(blank_db, "P2", ["Python", "FastAPI"])  

    def fake_get_skills(_session):
        return [
            WeightedSkills(skill_name="Python", weight=1.0),
            WeightedSkills(skill_name="React", weight=0.5),
            WeightedSkills(skill_name="FastAPI", weight=0.7),
        ]

    monkeypatch.setattr(skills_router, "get_skills", fake_get_skills)

    r = client.get("/skills/highlighted")
    assert r.status_code == 200, r.text

    names = [x["name"] for x in r.json()["skills"]]
    assert names == ["FastAPI", "Python", "React"]