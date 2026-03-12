from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.database.api.models import FileReportModel, ProjectReportModel, ResumeItemModel, ResumeModel
from src.interface.api.routers.interview import router as interview_router
from src.interface.api.routers.util import get_session
import src.services.interview_service as interview_service
from src.services.job_readiness_service import JobReadinessResult


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


def _test_client(blank_db) -> TestClient:
    app = FastAPI()
    app.include_router(interview_router)

    def _fake_get_session():
        with Session(blank_db) as session:
            yield session

    app.dependency_overrides[get_session] = _fake_get_session
    return TestClient(app)


def _fake_readiness_result() -> JobReadinessResult:
    return JobReadinessResult.model_validate(
        {
            "fit_score": 78,
            "summary": "Good backend fit with containerization gap.",
            "strengths": [
                {"item": "FastAPI APIs", "reason": "Project evidence shows routed backend work.", "rank": 1}
            ],
            "weaknesses": [
                {"item": "Docker deployment", "reason": "No deployment evidence was detected.", "rank": 1}
            ],
            "suggestions": [
                {
                    "item": "Containerize the service and document the deployment",
                    "reason": "This closes the clearest delivery gap.",
                    "priority": 1,
                    "action_type": "deploy project",
                    "resource_name": "Official Docker getting started guide",
                    "resource_type": "official tutorial",
                    "resource_hint": "Use it to build and run a local container for the current API.",
                }
            ],
        }
    )


def test_interview_start_endpoint_returns_first_question(blank_db, monkeypatch):
    _insert_resume_with_project(blank_db)
    client = _test_client(blank_db)

    monkeypatch.setattr(interview_service, "run_job_readiness_analysis", lambda **_: _fake_readiness_result())
    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(
        interview_service,
        "azure_chat_json",
        lambda **_: {
            "question": "Explain the architecture of your FastAPI project and why you chose it.",
            "question_category": "project_based",
            "interviewer_focus": "Probe system structure, tradeoffs, and ownership.",
        },
    )

    response = client.post(
        "/interview/start",
        json={
            "job_description": "Backend engineer with FastAPI, SQL, and scalable API design experience.",
            "resume_id": 1,
            "difficulty": "intermediate",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["question_category"] == "project_based"
    assert "architecture" in payload["question"].lower()


def test_interview_answer_endpoint_returns_feedback_and_next_question(blank_db, monkeypatch):
    _insert_resume_with_project(blank_db)
    client = _test_client(blank_db)

    monkeypatch.setattr(interview_service, "run_job_readiness_analysis", lambda **_: _fake_readiness_result())
    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(
        interview_service,
        "azure_chat_json",
        lambda **_: {
            "answer_acceptable": True,
            "feedback": {
                "strengths": "The answer clearly explained the API layers and data flow.",
                "improvements": "It should also mention scaling choices, database tradeoffs, and error handling.",
                "example_answer": "I structured the system around FastAPI routers, service logic, and a SQL-backed data layer so features stayed modular. I chose that split because it kept endpoint code thin and made testing and reporting queries easier. For higher traffic, I would optimize query patterns, add caching where reads are repetitive, and monitor slow endpoints before scaling horizontally.",
            },
            "next_question": "How would you optimize database queries for high traffic reporting endpoints?",
            "next_question_category": "role_specific",
        },
    )

    response = client.post(
        "/interview/answer",
        json={
            "job_description": "Backend engineer with FastAPI, SQL, and scalable API design experience.",
            "resume_id": 1,
            "difficulty": "advanced",
            "current_question": "Explain the architecture of your project.",
            "user_answer": "I used FastAPI routes with SQL reporting endpoints and tried to keep the backend modular.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "strengths" in payload["feedback"]
    assert payload["answer_acceptable"] is True
    assert payload["next_question_category"] == "role_specific"
    assert "database queries" in payload["next_question"].lower()


def test_generate_question_retries_once_when_output_is_invalid(monkeypatch):
    attempts = {"count": 0}

    def fake_azure_chat_json(**_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return {"question": "Bad shape only"}
        return {
            "question": "How would you containerize this FastAPI service for deployment?",
            "question_category": "skill_gap",
            "interviewer_focus": "Probe missing deployment depth and practical execution.",
        }

    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(interview_service, "azure_chat_json", fake_azure_chat_json)

    result = interview_service.generate_question(
        job_description="Backend engineer with Docker experience.",
        interview_context={
            "user_profile": {
                "resume_text": "Built APIs with FastAPI",
                "project_summaries": ["Inventory API with SQL reporting"],
                "tags": ["backend"],
                "extracted_skills": ["Python", "FastAPI", "SQL"],
                "repository_history_summary": [],
                "repository_file_evidence": [],
                "collaboration_signals": [],
            },
            "job_readiness_signals": {
                "strengths": [],
                "weaknesses": [{"item": "Docker deployment", "reason": "No Docker evidence", "rank": 1}],
                "suggestions": [],
            },
        },
    )

    assert result is not None
    assert result.question_category == "skill_gap"
    assert attempts["count"] == 2


def test_interview_start_returns_503_when_generation_unavailable(blank_db, monkeypatch):
    _insert_resume_with_project(blank_db)
    client = _test_client(blank_db)

    monkeypatch.setattr(interview_service, "run_job_readiness_analysis", lambda **_: None)
    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: False)

    response = client.post(
        "/interview/start",
        json={
            "job_description": "Backend engineer with FastAPI experience.",
            "resume_id": 1,
        },
    )

    assert response.status_code == 503


def test_evaluate_answer_insufficient_response_is_marked_by_model(monkeypatch):
    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(
        interview_service,
        "azure_chat_json",
        lambda **_: {
            "answer_acceptable": False,
            "feedback": {
                "strengths": "The answer acknowledged the prompt, but it did not provide technical substance.",
                "improvements": "The answer is too short to assess. Retry with a concrete explanation of your design, implementation steps, and tradeoffs.",
                "example_answer": "A stronger answer would explain the project context, the architecture or API decisions you made, one challenge you faced, and how you handled reliability, testing, or performance.",
            },
            "next_question": "Please answer again with specifics: how did you design the FastAPI service, and what tradeoffs did you consider?",
            "next_question_category": "project_based",
        },
    )

    result = interview_service.evaluate_answer(
        user_answer="yes",
        current_question="Explain how you designed the FastAPI service.",
        job_description="Backend engineer with API design experience.",
        interview_context={
            "user_profile": {
                "resume_text": "Built backend APIs",
                "project_summaries": ["FastAPI order service"],
                "tags": ["backend"],
                "extracted_skills": ["Python", "FastAPI", "SQL"],
                "repository_history_summary": [],
                "repository_file_evidence": [],
                "collaboration_signals": [],
            },
            "job_readiness_signals": {
                "strengths": [],
                "weaknesses": [],
                "suggestions": [],
            },
        },
    )

    assert result is not None
    assert result.answer_acceptable is False
    assert "too short" in result.feedback.improvements.lower()
    assert result.next_question_category == "project_based"
