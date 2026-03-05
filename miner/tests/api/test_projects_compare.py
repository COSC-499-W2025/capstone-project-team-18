import datetime
from types import SimpleNamespace
from urllib.parse import quote

from sqlmodel import Session

from src.database.api.models import ProjectReportModel
import importlib

projects_module = importlib.import_module("src.interface.api.routers.projects")

def _insert_project(engine, name: str, created_at: datetime.datetime, rank=None, compare=None, start=None, end=None):
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

            representation_rank=rank,
            compare_attributes=compare or [],
            chrono_start_override=start,
            chrono_end_override=end,
            showcase_selected=False,
            highlight_skills=[],

            showcase_title=None,
            showcase_start_date=None,
            showcase_end_date=None,
            showcase_frameworks=[],
            showcase_bullet_points=[],
            showcase_last_user_edit_at=None,
        )
        session.add(m)
        session.commit()


def test_compare_projects_unions_attributes_and_sorts(client, blank_db, monkeypatch):
    now = datetime.datetime.now()

    _insert_project(blank_db, "A", now + datetime.timedelta(seconds=1), rank=1, compare=["frameworks", "weight"])
    _insert_project(blank_db, "B", now + datetime.timedelta(seconds=2), rank=0, compare=["start_date", "end_date"])

    def fake_get_project_report_by_name(_session, project_name: str):
        if project_name == "A":
            item = SimpleNamespace(
                start_date=datetime.date(2026, 1, 1),
                end_date=datetime.date(2026, 2, 1),
                frameworks=["FastAPI", "React"],
                bullet_points=[],
                title="A",
            )
            return SimpleNamespace(generate_resume_item=lambda: item, get_project_weight=lambda: 2.5)

        if project_name == "B":
            item = SimpleNamespace(
                start_date=datetime.date(2025, 5, 1),
                end_date=datetime.date(2025, 6, 1),
                frameworks=["Python"],
                bullet_points=[],
                title="B",
            )
            return SimpleNamespace(generate_resume_item=lambda: item, get_project_weight=lambda: 1.0)

        return None

    monkeypatch.setattr(projects_module, "get_project_report_by_name", fake_get_project_report_by_name)

    r = client.get("/projects/compare?projects=A,B")
    assert r.status_code == 200, r.text
    body = r.json()

    # union (sorted)
    assert body["attributes"] == ["end_date", "frameworks", "start_date", "weight"]

    # sorted by representation_rank: B(0) then A(1)
    names = [p["project_name"] for p in body["projects"]]
    assert names == ["B", "A"]

    # check resolved fields exist
    b_attrs = body["projects"][0]["attributes"]
    assert b_attrs["start_date"].startswith("2025-05-01")
    assert b_attrs["end_date"].startswith("2025-06-01")
    assert b_attrs["frameworks"] == ["Python"]
    assert b_attrs["weight"] == 1.0


def test_compare_projects_404_if_missing(client, blank_db):
    now = datetime.datetime.now()
    _insert_project(blank_db, "A", now, rank=0, compare=["weight"])

    r = client.get("/projects/compare?projects=A,Nope")
    assert r.status_code == 404
    assert "Missing project" in r.json().get("detail", "")