import datetime
from urllib.parse import quote

from sqlmodel import Session

from src.database.api.models import ProjectReportModel


def _insert_project(engine, project_name: str, created_at: datetime.datetime) -> None:
    """
    Insert a minimal ProjectReportModel row that satisfies NOT NULL constraints.
    """
    with Session(engine) as session:
        model = ProjectReportModel(
            project_name=project_name,
            user_config_used=None,
            image_data=None,
            statistic={"dummy": True},
            created_at=created_at,
            last_updated=created_at,
            analyzed_count=1,
            parent=None,

            compare_attributes=[],
            highlight_skills=[],
            showcase_selected=False,
            representation_rank=None,

            # keep showcase overrides default-ish (safe)
            showcase_title=None,
            showcase_start_date=None,
            showcase_end_date=None,
            showcase_frameworks=[],
            showcase_bullet_points=[],
            showcase_last_user_edit_at=None,
        )
        session.add(model)
        session.commit()


def test_reorder_persists_and_get_projects_returns_sorted(client, blank_db):
    """
    - insert 3 ProjectReportModels into blank_db
    - PUT /projects/representation/reorder with order [B, A, C]
    - GET /projects and assert order is [B, A, C]
    """
    now = datetime.datetime.now()

    # Use distinct created_at values just to avoid any tie weirdness if needed
    _insert_project(blank_db, "A", now + datetime.timedelta(seconds=1))
    _insert_project(blank_db, "B", now + datetime.timedelta(seconds=2))
    _insert_project(blank_db, "C", now + datetime.timedelta(seconds=3))

    payload = {"project_names": ["B", "A", "C"]}
    r = client.put("/projects/representation/reorder", json=payload)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    r2 = client.get("/projects/")
    assert r2.status_code == 200, r2.text
    body = r2.json()

    names = [p["project_name"] for p in body["projects"]]
    assert names == ["B", "A", "C"]


def test_chronology_override_validation_422(client, blank_db):
    """
    PATCH /projects/{name}/representation with chrono_start_override > chrono_end_override
    should return 422.
    """
    now = datetime.datetime.now()
    _insert_project(blank_db, "Demo Project", now)

    bad_payload = {
        "chrono_start_override": "2026-02-02T00:00:00",
        "chrono_end_override": "2026-01-01T00:00:00",
    }

    r = client.patch(f"/projects/{quote('Demo Project')}/representation", json=bad_payload)
    assert r.status_code == 422, r.text

    # Your router raises: detail="chrono_end_override must be >= chrono_start_override"
    detail = r.json().get("detail", "")
    assert "chrono_end_override" in detail


def test_showcase_selection_persisted(client, blank_db):
    """
    PATCH showcase_selected=True and verify the model is updated in the DB.
    """
    now = datetime.datetime.now()
    _insert_project(blank_db, "Demo Project", now)

    payload = {"showcase_selected": True}

    r = client.patch(f"/projects/{quote('Demo Project')}/representation", json=payload)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    with Session(blank_db) as session:
        model = session.get(ProjectReportModel, "Demo Project")
        assert model is not None
        assert model.showcase_selected is True