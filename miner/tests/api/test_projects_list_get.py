"""
Tests for GET /projects/ and GET /projects/{project_name}
"""
import datetime

import pytest
from sqlmodel import Session

from src.database.api.models import ProjectReportModel
from src.interface.api.routers.util import get_session


def _insert_project(engine, name: str, rank=None, created_at=None):
    now = created_at or datetime.datetime.now()
    with Session(engine) as session:
        session.add(ProjectReportModel(
            project_name=name,
            statistic={"dummy": True},
            created_at=now,
            last_updated=now,
            representation_rank=rank,
        ))
        session.commit()


# ---------------------------------------------------------------------------
# GET /projects/
# ---------------------------------------------------------------------------

class TestListProjects:
    def test_returns_empty_list_when_no_projects(self, client, blank_db):
        r = client.get("/projects/")
        assert r.status_code == 200
        body = r.json()
        assert body["projects"] == []
        assert body["count"] == 0

    def test_returns_all_projects(self, client, blank_db):
        _insert_project(blank_db, "alpha")
        _insert_project(blank_db, "beta")
        r = client.get("/projects/")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 2
        names = {p["project_name"] for p in body["projects"]}
        assert names == {"alpha", "beta"}

    def test_count_matches_projects_length(self, client, blank_db):
        for i in range(5):
            _insert_project(blank_db, f"proj-{i}")
        r = client.get("/projects/")
        body = r.json()
        assert body["count"] == len(body["projects"])

    def test_sorted_by_representation_rank_asc(self, client, blank_db):
        now = datetime.datetime.now()
        _insert_project(blank_db, "C", rank=2, created_at=now)
        _insert_project(blank_db, "A", rank=0, created_at=now)
        _insert_project(blank_db, "B", rank=1, created_at=now)
        r = client.get("/projects/")
        names = [p["project_name"] for p in r.json()["projects"]]
        assert names == ["A", "B", "C"]

    def test_unranked_projects_sorted_last(self, client, blank_db):
        now = datetime.datetime.now()
        _insert_project(blank_db, "ranked", rank=0, created_at=now)
        _insert_project(blank_db, "unranked", rank=None, created_at=now)
        r = client.get("/projects/")
        names = [p["project_name"] for p in r.json()["projects"]]
        assert names[0] == "ranked"
        assert names[-1] == "unranked"

    def test_response_contains_expected_fields(self, client, blank_db):
        _insert_project(blank_db, "my-proj")
        r = client.get("/projects/")
        project = r.json()["projects"][0]
        for field in ("project_name", "statistic", "created_at", "last_updated"):
            assert field in project

    def test_returns_500_on_db_error(self, client, monkeypatch):
        import sys
        import src.interface.api.routers.projects  # ensure module is loaded
        projects_mod = sys.modules["src.interface.api.routers.projects"]
        monkeypatch.setattr(
            projects_mod, "get_all_project_report_models",
            lambda session: (_ for _ in ()).throw(RuntimeError("db boom"))
        )
        r = client.get("/projects/")
        assert r.status_code == 500

    def test_image_data_is_base64_string_when_present(self, client, blank_db):
        now = datetime.datetime.now()
        with Session(blank_db) as session:
            session.add(ProjectReportModel(
                project_name="img-proj",
                statistic={},
                created_at=now,
                last_updated=now,
                image_data=b"\x89PNG",
            ))
            session.commit()
        r = client.get("/projects/")
        project = next(p for p in r.json()["projects"] if p["project_name"] == "img-proj")
        assert isinstance(project["image_data"], str)

    def test_image_data_is_null_when_absent(self, client, blank_db):
        _insert_project(blank_db, "no-img")
        r = client.get("/projects/")
        project = r.json()["projects"][0]
        assert project["image_data"] is None


# ---------------------------------------------------------------------------
# GET /projects/{project_name}
# ---------------------------------------------------------------------------

class TestGetProject:
    def test_returns_project_by_name(self, client, blank_db):
        _insert_project(blank_db, "target")
        r = client.get("/projects/target")
        assert r.status_code == 200
        assert r.json()["project_name"] == "target"

    def test_returns_404_when_not_found(self, client, blank_db):
        r = client.get("/projects/does-not-exist")
        assert r.status_code == 404
        assert r.json()["error_code"] == "PROJECT_NOT_FOUND"

    def test_returns_500_on_db_error(self, client, monkeypatch):
        import sys
        import src.interface.api.routers.projects  # ensure module is loaded
        projects_mod = sys.modules["src.interface.api.routers.projects"]
        monkeypatch.setattr(
            projects_mod, "get_project_report_model_by_name",
            lambda session, name: (_ for _ in ()).throw(RuntimeError("db boom"))
        )
        r = client.get("/projects/any-project")
        assert r.status_code == 500
        assert r.json()["error_code"] == "DATABASE_OPERATION_FAILED"

    def test_response_contains_statistic(self, client, blank_db):
        now = datetime.datetime.now()
        with Session(blank_db) as session:
            session.add(ProjectReportModel(
                project_name="stat-proj",
                statistic={"lines": 42},
                created_at=now,
                last_updated=now,
            ))
            session.commit()
        r = client.get("/projects/stat-proj")
        assert r.json()["statistic"]["lines"] == 42

    def test_project_name_is_case_sensitive(self, client, blank_db):
        _insert_project(blank_db, "MyProject")
        r = client.get("/projects/myproject")
        assert r.status_code == 404
