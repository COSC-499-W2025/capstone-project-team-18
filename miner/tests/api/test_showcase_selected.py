import datetime
from types import SimpleNamespace

from sqlmodel import Session

from src.database.api.models import ProjectReportModel
import importlib

projects_module = importlib.import_module("src.interface.api.routers.projects")

def _insert_project(engine, name: str, created_at: datetime.datetime, selected: bool, rank=None):
    with Session(engine) as session:
        m = ProjectReportModel(
            project_name=name,
            user_config_used=None,
            image_data=None,
            statistic={"dummy": True},
            created_at=created_at,
            last_updated=created_at,
            analyzed_count=1,
            parent=None,

            showcase_selected=selected,
            representation_rank=rank,
            compare_attributes=[],
            highlight_skills=[],
            representation_last_user_edit_at=None,

            showcase_title=None,
            showcase_start_date=None,
            showcase_end_date=None,
            showcase_frameworks=[],
            showcase_bullet_points=[],
            showcase_last_user_edit_at=None,
        )
        session.add(m)
        session.commit()


def test_get_selected_showcase_projects_filters_and_sorts(client, blank_db, monkeypatch):
    now = datetime.datetime.now()

    # A (selected, rank=1), B (selected, rank=0), C (not selected)
    _insert_project(blank_db, "A", now + datetime.timedelta(seconds=1), selected=True, rank=1)
    _insert_project(blank_db, "B", now + datetime.timedelta(seconds=2), selected=True, rank=0)
    _insert_project(blank_db, "C", now + datetime.timedelta(seconds=3), selected=False, rank=2)

    def fake_get_project_report_by_name(_session, project_name: str):
        fake_resume_item = SimpleNamespace(
            title=f"Generated {project_name}",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 2, 1),
            frameworks=["Python"],
            bullet_points=[f"Did {project_name} things"],
        )
        return SimpleNamespace(
            project_name=project_name,
            generate_resume_item=lambda: fake_resume_item,
        )

    monkeypatch.setattr(projects_module, "get_project_report_by_name", fake_get_project_report_by_name)

    r = client.get("/projects/showcase/selected")
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["count"] == 2

    names = [p["project_name"] for p in body["projects"]]
    assert names == ["B", "A"]

    # spot-check format
    first = body["projects"][0]
    assert first["title"].startswith("Generated")
    assert first["frameworks"] == ["Python"]
    assert first["bullet_points"] == ["Did B things"]
    assert first["start_date"].startswith("2026-01-01")
    assert first["end_date"].startswith("2026-02-01")