from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.database.api.models import FileReportModel, ProjectReportModel, ResumeItemModel, ResumeModel
from src.interface.api.routers.job_readiness import router as job_readiness_router
from src.interface.api.routers.util import get_session
from src.services import job_readiness_service


def _insert_resume_with_project(blank_db) -> None:
    with Session(blank_db) as session:
        resume = ResumeModel(
            id=1,
            email="candidate@example.com",
            github="candidate",
            skills=["Python", "FastAPI", "SQL"],
            created_at=datetime(2026, 3, 1, 12, 0, 0),
            last_updated=datetime(2026, 3, 1, 12, 0, 0),
        )
        resume.items = [
            ResumeItemModel(
                id=1,
                resume_id=1,
                project_name="InventoryAPI",
                title="Backend Developer",
                frameworks=["FastAPI", "PostgreSQL"],
                bullet_points=[
                    "Built REST APIs for inventory workflows",
                    "Implemented SQL reporting endpoints",
                ],
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
            )
        ]

        project = ProjectReportModel(
            project_name="InventoryAPI",
            statistic={"commits": 42, "primary_language": "Python"},
            created_at=datetime(2026, 2, 20, 10, 0, 0),
            last_updated=datetime(2026, 2, 25, 9, 0, 0),
            analyzed_count=1,
            showcase_title="Inventory Platform",
            showcase_frameworks=["FastAPI", "PostgreSQL"],
            showcase_bullet_points=["Shipped stock tracking API", "Added SQL-backed dashboards"],
        )
        project.file_reports = [
            FileReportModel(
                project_name="InventoryAPI",
                file_path="api/routes/inventory.py",
                is_info_file=False,
                statistic={"lines": 120},
            ),
            FileReportModel(
                project_name="InventoryAPI",
                file_path="db/reporting.sql",
                is_info_file=False,
                statistic={"lines": 40},
            ),
        ]

        session.add(resume)
        session.add(project)
        session.commit()


def _valid_result(summary: str = "Strong backend alignment.") -> dict:
    return {
        "fit_score": 82,
        "summary": summary,
        "strengths": [
            {"item": "FastAPI backend work", "reason": "Supported by resume bullets and project evidence.", "rank": 1}
        ],
        "weaknesses": [
            {"item": "Cloud deployment depth", "reason": "Evidence bundle does not show production Azure deployment.", "rank": 1}
        ],
        "suggestions": [
            {
                "item": "Add Azure deployment evidence",
                "reason": "This would close the clearest platform gap.",
                "priority": 1,
                "action_type": "deploy project",
                "resource_name": "Microsoft Learn Azure deployment tutorial",
                "resource_type": "guided learning path",
                "resource_hint": "Use it to deploy a small Python API demo and add the deployment as a portfolio artifact.",
            }
        ],
    }


def _test_client(blank_db) -> TestClient:
    app = FastAPI()
    app.include_router(job_readiness_router)

    def _fake_get_session():
        with Session(blank_db) as session:
            yield session

    app.dependency_overrides[get_session] = _fake_get_session
    return TestClient(app)


def test_job_readiness_endpoint_returns_valid_analysis(blank_db, monkeypatch):
    _insert_resume_with_project(blank_db)
    client = _test_client(blank_db)

    monkeypatch.setattr(job_readiness_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(job_readiness_service, "azure_chat_json", lambda **_: _valid_result())

    response = client.post(
        "/job-readiness/analyze",
        json={
            "job_description": "Backend engineer with FastAPI, SQL, and API design experience.",
            "resume_id": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fit_score"] == 82
    assert payload["strengths"][0]["rank"] == 1
    assert payload["suggestions"][0]["priority"] == 1
    assert payload["suggestions"][0]["resource_type"] == "guided learning path"


def test_job_readiness_retries_once_when_llm_output_is_invalid(monkeypatch):
    attempts = {"count": 0}

    def fake_azure_chat_json(**_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return {"fit_score": "bad-shape"}
        return _valid_result("Recovered after retry.")

    monkeypatch.setattr(job_readiness_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(job_readiness_service, "azure_chat_json", fake_azure_chat_json)

    result = job_readiness_service.run_job_readiness_analysis(
        job_description="Data analyst with SQL and dashboard experience.",
        user_profile={
            "resume_text": "Skills: SQL, Python, dashboards",
            "project_summaries": ["Built reporting dashboards"],
            "tags": ["analytics"],
            "extracted_skills": ["SQL", "Python"],
            "repository_history_summary": [],
            "repository_file_evidence": [],
        },
    )

    assert result is not None
    assert result.summary == "Recovered after retry."
    assert attempts["count"] == 2


def test_job_readiness_retries_when_suggestion_is_generic(monkeypatch):
    attempts = {"count": 0}

    def fake_azure_chat_json(**_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            bad = _valid_result("Generic suggestion should fail.")
            bad["suggestions"][0]["item"] = "Learn Flask"
            bad["suggestions"][0]["action_type"] = "course"
            bad["suggestions"][0]["resource_name"] = "Official Flask tutorial"
            bad["suggestions"][0]["resource_type"] = "official tutorial"
            bad["suggestions"][0]["resource_hint"] = "Read the getting started guide."
            return bad
        return _valid_result("Recovered after actionable retry.")

    monkeypatch.setattr(job_readiness_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(job_readiness_service, "azure_chat_json", fake_azure_chat_json)

    result = job_readiness_service.run_job_readiness_analysis(
        job_description="Backend engineer with Flask experience.",
        user_profile={
            "resume_text": "FastAPI backend work",
            "project_summaries": ["Built REST APIs"],
            "tags": ["backend"],
            "extracted_skills": ["Python", "FastAPI"],
            "repository_history_summary": [],
            "repository_file_evidence": [],
        },
    )

    assert result is not None
    assert result.summary == "Recovered after actionable retry."
    assert attempts["count"] == 2


def test_job_readiness_accepts_inline_user_profile_only(blank_db, monkeypatch):
    client = _test_client(blank_db)

    monkeypatch.setattr(job_readiness_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(
        job_readiness_service,
        "azure_chat_json",
        lambda **_: _valid_result("Inline evidence was sufficient."),
    )

    response = client.post(
        "/job-readiness/analyze",
        json={
            "job_description": "Frontend engineer with React and TypeScript experience.",
            "user_profile": {
                "resume_text": "Built React dashboards and TypeScript UI components.",
                "project_summaries": ["Created a component library for internal tools."],
                "tags": ["frontend", "design systems"],
                "extracted_skills": ["React", "TypeScript"],
                "repository_history_summary": [],
                "repository_file_evidence": [],
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Inline evidence was sufficient."


def test_job_readiness_basic_role_coverage(monkeypatch):
    monkeypatch.setattr(job_readiness_service, "azure_openai_enabled", lambda: True)

    def fake_azure_chat_json(*, user_prompt, **_kwargs):
        if "Backend engineer" in user_prompt:
            return _valid_result("Backend role covered.")
        if "Data analyst" in user_prompt:
            return _valid_result("Data role covered.")
        return _valid_result("Frontend role covered.")

    monkeypatch.setattr(job_readiness_service, "azure_chat_json", fake_azure_chat_json)

    role_expectations = [
        ("Backend engineer with Python APIs.", "Backend role covered."),
        ("Data analyst with SQL and dashboards.", "Data role covered."),
        ("Frontend engineer with React.", "Frontend role covered."),
    ]

    for job_description, expected_summary in role_expectations:
        result = job_readiness_service.run_job_readiness_analysis(
            job_description=job_description,
            user_profile={
                "resume_text": "General software evidence",
                "project_summaries": [],
                "tags": [],
                "extracted_skills": ["Python"],
                "repository_history_summary": [],
                "repository_file_evidence": [],
            },
        )
        assert result is not None
        assert result.summary == expected_summary
