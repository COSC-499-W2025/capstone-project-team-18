import datetime, pytest, importlib
from types import SimpleNamespace

from sqlmodel import Session

from src.database.api.models import ProjectReportModel

projects_module = importlib.import_module("src.interface.api.routers.projects")


def _insert_project(engine, project_name: str = "Demo Project") -> None:
    with Session(engine) as session:
        model = ProjectReportModel(
            project_name=project_name,
            user_config_used=None,
            image_data=None,
            statistic={"dummy": True},
            created_at=datetime.datetime.now(),
            last_updated=datetime.datetime.now(),
            # showcase fields default to None
            showcase_title=None,
            showcase_start_date=None,
            showcase_end_date=None,
            showcase_frameworks=None,
            showcase_bullet_points=None,
            showcase_last_user_edit_at=None,
        )
        session.add(model)
        session.commit()


def test_put_customization_persists_and_get_returns_saved(client, blank_db):
    _insert_project(blank_db, "Demo Project")

    payload = {
        "title": "My Custom Title",
        "frameworks": ["HTML", "CSS", "JavaScript"],
        "bullet_points": ["A", "B", "C"],
        "start_date": "2026-01-01T00:00:00",
        "end_date": "2026-02-01T00:00:00",
    }

    r = client.put("/projects/Demo%20Project/showcase/customization", json=payload)
    assert r.status_code == 200
    assert r.json().get("ok") is True

    r2 = client.get("/projects/Demo%20Project/showcase/customization")
    assert r2.status_code == 200
    saved = r2.json()

    assert saved["project_name"] == "Demo Project"
    assert saved["title"] == "My Custom Title"
    assert saved["frameworks"] == ["HTML", "CSS", "JavaScript"]
    assert saved["bullet_points"] == ["A", "B", "C"]
    assert saved["last_user_edit_at"] is not None


def test_get_customization_404_when_project_missing(client):
    r = client.get("/projects/Nope/showcase/customization")
    assert r.status_code == 404


def test_delete_customization_clears_fields(client, blank_db):
    _insert_project(blank_db, "Demo Project")

    with Session(blank_db) as session:
        model = session.get(ProjectReportModel, "Demo Project")
        assert model is not None
        model.showcase_title = "Temp"
        model.showcase_frameworks = ["X"]
        model.showcase_bullet_points = ["Y"]
        model.showcase_last_user_edit_at = datetime.datetime.now()
        session.add(model)
        session.commit()

    r = client.delete("/projects/Demo%20Project/showcase/customization")
    assert r.status_code == 200
    assert r.json().get("ok") is True

    r2 = client.get("/projects/Demo%20Project/showcase/customization")
    assert r2.status_code == 200
    data = r2.json()

    assert data["title"] is None
    assert data["frameworks"] == []
    assert data["bullet_points"] == []
    assert data["last_user_edit_at"] is None


def test_showcase_merges_overrides_over_defaults(client, blank_db, monkeypatch):
    _insert_project(blank_db, "Demo Project")

    # Save overrides first
    payload = {
        "title": "Portfolio Showcase: Demo Project",
        "frameworks": ["FastAPI", "React"],
        "bullet_points": ["Custom 1", "Custom 2"],
    }
    r = client.put("/projects/Demo%20Project/showcase/customization", json=payload)
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # Mock domain object retrieval so we don't depend on heavy ProjectReport internals
    def fake_get_project_report_by_name(_session, project_name: str):
        assert project_name == "Demo Project"
        fake_resume_item = SimpleNamespace(
            title="Generated Title",
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            frameworks=["../images/a.png", "https://example.com/font.css", "Python"],
            bullet_points=["Generated bullet"],
        )
        return SimpleNamespace(
            project_name=project_name,
            generate_resume_item=lambda: fake_resume_item,
        )

    monkeypatch.setattr(projects_module, "get_project_report_by_name", fake_get_project_report_by_name)

    r2 = client.get("/projects/Demo%20Project/showcase")
    assert r2.status_code == 200
    out = r2.json()

    assert out["project_name"] == "Demo Project"
    assert out["title"] == "Portfolio Showcase: Demo Project"
    assert out["frameworks"] == ["FastAPI", "React"]
    assert out["bullet_points"] == ["Custom 1", "Custom 2"]

    # Dates should still be present via defaults if not overridden
    assert out["start_date"] is not None
    assert out["end_date"] is not None


def test_showcase_returns_404_when_project_missing(client, monkeypatch):
    monkeypatch.setattr(projects_module, "get_project_report_by_name", lambda *_a, **_kw: None)
    r = client.get("/projects/Nope/showcase")
    assert r.status_code == 404


def test_showcase_returns_500_when_crud_raises(client, monkeypatch):
    def boom(*_a, **_kw):
        raise RuntimeError("DB failed")

    monkeypatch.setattr(projects_module, "get_project_report_by_name", boom)

    r = client.get("/projects/Demo/showcase")
    assert r.status_code == 500
    assert "Failed to retrieve project report" in r.json().get("message", "")

def test_showcase_defaults_when_no_overrides(client, blank_db, monkeypatch):
    _insert_project(blank_db, "Demo Project")

    def fake_get_project_report_by_name(_session, project_name: str):
        assert project_name == "Demo Project"
        fake_resume_item = SimpleNamespace(
            title="Generated Title",
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            frameworks=["Python"],
            bullet_points=["Generated bullet"],
        )
        return SimpleNamespace(
            project_name=project_name,
            generate_resume_item=lambda: fake_resume_item,
        )

    monkeypatch.setattr(projects_module, "get_project_report_by_name", fake_get_project_report_by_name)

    r = client.get("/projects/Demo%20Project/showcase")
    assert r.status_code == 200, r.text
    out = r.json()

    assert out["project_name"] == "Demo Project"
    assert out["title"] == "Generated Title"
    assert out["frameworks"] == ["Python"]
    assert out["bullet_points"] == ["Generated bullet"]
    assert out["start_date"].startswith("2025-01-01")
    assert out["end_date"].startswith("2025-12-31")

def test_showcase_respects_chronology_override(client, blank_db, monkeypatch):
    _insert_project(blank_db, "Demo Project")

    from sqlmodel import Session
    from src.database.api.models import ProjectReportModel

    with Session(blank_db) as session:
        m = session.get(ProjectReportModel, "Demo Project")
        m.chrono_start_override = datetime.datetime(2024, 1, 1)
        m.chrono_end_override = datetime.datetime(2024, 2, 1)
        session.add(m)
        session.commit()

    def fake_get_project_report_by_name(_session, project_name):
        fake_resume_item = SimpleNamespace(
            title="Generated",
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 2, 1),
            frameworks=["Python"],
            bullet_points=["A"],
        )
        return SimpleNamespace(
            project_name=project_name,
            generate_resume_item=lambda: fake_resume_item,
        )

    monkeypatch.setattr(projects_module, "get_project_report_by_name", fake_get_project_report_by_name)

    r = client.get("/projects/Demo%20Project/showcase")
    assert r.status_code == 200
    out = r.json()

    assert out["start_date"].startswith("2024-01-01")
    assert out["end_date"].startswith("2024-02-01")