from datetime import datetime, date
from fastapi.testclient import TestClient
import importlib

from src.interface.api.api import app

projects_mod = importlib.import_module("src.interface.api.routers.projects")

client = TestClient(app)

class ResumeItemStub:
    def __init__(self, title="Demo Title", start_date=None, end_date=None, frameworks=None, bullet_points=None):
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.frameworks = frameworks or []
        self.bullet_points = bullet_points or []

class WeightedSkillStub:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight

class ProjectReportStub:
    def __init__(self, project_name: str, resume_item: ResumeItemStub):
        self.project_name = project_name
        self._resume_item = resume_item

    def generate_resume_item(self):
        return self._resume_item

def test_showcase_success_200(monkeypatch):
    stub_report = ProjectReportStub(
        "DemoProject",
        ResumeItemStub(
            start_date=date(2026, 2, 1),
            end_date=datetime(2026, 2, 20, 12, 30, 0),
            frameworks=["FastAPI", "React"],
            bullet_points=["Built X", "Improved Y"],
        ),
    )

    def fake_get_project_report_by_name(session, project_name: str):
        assert project_name == "DemoProject"
        return stub_report

    monkeypatch.setattr(projects_mod, "get_project_report_by_name", fake_get_project_report_by_name)

    res = client.get("/projects/DemoProject/showcase")
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["project_name"] == "DemoProject"
    assert body["frameworks"] == ["FastAPI", "React"]
    assert body["bullet_points"] == ["Built X", "Improved Y"]
    assert body["start_date"].startswith("2026-02-01T00:00:00")
    assert body["end_date"].startswith("2026-02-20T12:30:00")

def test_showcase_404(monkeypatch):
    def fake_get_project_report_by_name(session, project_name: str):
        return None

    monkeypatch.setattr(projects_mod, "get_project_report_by_name", fake_get_project_report_by_name)

    res = client.get("/projects/Nope/showcase")
    assert res.status_code == 404
    assert "No project report named" in res.json()["detail"]

def test_showcase_500(monkeypatch):
    def fake_get_project_report_by_name(session, project_name: str):
        raise RuntimeError("Database connection failed")

    monkeypatch.setattr(projects_mod, "get_project_report_by_name", fake_get_project_report_by_name)

    res = client.get("/projects/Any/showcase")
    assert res.status_code == 500
    assert "Failed to retrieve project report" in res.json()["detail"]

def test_showcase_frameworks_weighted_skill_normalized(monkeypatch):
    stub_report = ProjectReportStub(
        "DemoProject",
        ResumeItemStub(
            start_date=date(2026, 2, 1),
            end_date=datetime(2026, 2, 20, 12, 30, 0),
            frameworks=[WeightedSkillStub("FastAPI", 0.9)],
            bullet_points=["Built X"],
        ),
    )

    def fake_get_project_report_by_name(session, project_name: str):
        assert project_name == "DemoProject"
        return stub_report

    monkeypatch.setattr(projects_mod, "get_project_report_by_name", fake_get_project_report_by_name)

    res = client.get("/projects/DemoProject/showcase")
    assert res.status_code == 200, res.text

    assert res.json()["frameworks"] == ["FastAPI"]

def test_resume_item_success_200(monkeypatch):
    stub_report = ProjectReportStub(
        "DemoProject",
        ResumeItemStub(
            title="Digital Artifact Miner",
            start_date=date(2026, 2, 1),
            end_date=datetime(2026, 2, 20, 12, 30, 0),
            frameworks=[WeightedSkillStub("FastAPI", 0.9), WeightedSkillStub("React", 0.8)],
            bullet_points=["Built X", "Improved Y"],
        ),
    )

    def fake_get_project_report_by_name(session, project_name: str):
        assert project_name == "DemoProject"
        return stub_report

    monkeypatch.setattr(projects_mod, "get_project_report_by_name", fake_get_project_report_by_name)

    res = client.get("/projects/DemoProject/resume-item")
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["title"] == "Digital Artifact Miner"
    assert body["frameworks"] == ["FastAPI", "React"]
    assert body["bullet_points"] == ["Built X", "Improved Y"]
    assert body["start_date"].startswith("2026-02-01T00:00:00")
    assert body["end_date"].startswith("2026-02-20T12:30:00")

def test_resume_item_404(monkeypatch):
    def fake_get_project_report_by_name(session, project_name: str):
        return None

    monkeypatch.setattr(projects_mod, "get_project_report_by_name", fake_get_project_report_by_name)

    res = client.get("/projects/Nope/resume-item")
    assert res.status_code == 404
    assert "No project report named" in res.json()["detail"]

def test_resume_item_500(monkeypatch):
    def fake_get_project_report_by_name(session, project_name: str):
        raise RuntimeError("Database connection failed")

    monkeypatch.setattr(projects_mod, "get_project_report_by_name", fake_get_project_report_by_name)

    res = client.get("/projects/Any/resume-item")
    assert res.status_code == 500
    assert "Failed to retrieve project report" in res.json()["detail"]