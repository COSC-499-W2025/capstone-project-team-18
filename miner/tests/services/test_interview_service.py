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
            "fit_dimension": "architecture",
            "project_name": "InventoryAPI",
            "next_action": "advance_dimension",
        },
    )

    response = client.post(
        "/interview/start",
        json={
            "job_description": "Backend engineer with FastAPI, SQL, and scalable API design experience.",
            "resume_id": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["question_category"] == "project_based"
    assert payload["fit_dimension"] == "architecture"
    assert payload["project_name"] == "InventoryAPI"
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
            "fit_dimension": "performance",
            "project_name": "InventoryAPI",
            "next_action": "advance_dimension",
        },
    )

    response = client.post(
        "/interview/answer",
        json={
            "job_description": "Backend engineer with FastAPI, SQL, and scalable API design experience.",
            "resume_id": 1,
            "current_question": "Explain the architecture of your project.",
            "user_answer": "I used FastAPI routes with SQL reporting endpoints and tried to keep the backend modular.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "strengths" in payload["feedback"]
    assert payload["answer_acceptable"] is True
    assert payload["next_question_category"] == "role_specific"
    assert payload["fit_dimension"] == "performance"
    assert payload["project_name"] == "InventoryAPI"
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
            "fit_dimension": "deployment",
            "project_name": "InventoryAPI",
            "next_action": "probe_gap",
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
    assert result.fit_dimension == "deployment"
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
            "fit_dimension": "architecture",
            "project_name": "InventoryAPI",
            "next_action": "retry_same_question",
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
    assert result.next_action == "retry_same_question"


def test_parse_answer_payload_repairs_blank_feedback_fields():
    payload = {
        "answer_acceptable": False,
        "feedback": {
            "strengths": "",
            "improvements": "Too vague.",
            "example_answer": "",
        },
        "next_question": "Retry with more detail about your API design decisions.",
        "next_question_category": "project_based",
    }

    result = interview_service._parse_answer_payload(  # type: ignore[attr-defined]
        payload,
        fit_dimension="architecture",
        project_name="InventoryAPI",
        interview_context={},
        user_answer="",
    )

    assert result is not None
    assert result.feedback.strengths
    assert result.feedback.example_answer
    assert result.fit_dimension == "architecture"
    assert result.project_name == "InventoryAPI"
    assert result.next_action == "retry_same_question"


def test_evaluate_answer_rotates_dimension_after_repeated_followups(monkeypatch):
    calls = {"count": 0}

    def fake_azure_chat_json(**kwargs):
        calls["count"] += 1
        schema_name = kwargs.get("schema_name")
        if schema_name == interview_service.DEFAULT_INTERVIEW_ANSWER_SCHEMA_NAME:
            return {
                "answer_acceptable": True,
                "feedback": {
                    "strengths": "The answer explained the testing approach clearly.",
                    "improvements": "It could mention one concrete tool or failure case.",
                    "example_answer": "I tested the main API flows and failure cases so the service contract stayed reliable.",
                },
                "next_question": "Can you describe another testing challenge you faced?",
                "next_question_category": "project_based",
                "fit_dimension": "testing",
                "project_name": "InventoryAPI",
                "next_action": "advance_dimension",
            }
        return {
            "question": "How did you reason about database query design in this project?",
            "question_category": "project_based",
            "interviewer_focus": "Probe database reasoning after enough testing depth.",
            "fit_dimension": "database",
            "project_name": "InventoryAPI",
            "next_action": "advance_dimension",
        }

    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(interview_service, "azure_chat_json", fake_azure_chat_json)

    result = interview_service.evaluate_answer(
        user_answer="I focused on core endpoint flows and error cases to keep the API reliable.",
        current_question="How did you approach testing the API endpoints?",
        job_description="Backend engineer with SQL and API experience.",
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
            "job_readiness_signals": {"strengths": [], "weaknesses": [], "suggestions": []},
            "job_fit_context": {
                "prioritized_dimensions": [
                    {"dimension": "testing", "label": "testing strategy", "matches": []},
                    {"dimension": "database", "label": "database reasoning", "matches": []},
                ],
                "relevant_projects": [
                    {
                        "project_name": "InventoryAPI",
                        "summary": "FastAPI order service",
                        "tech_stack": ["FastAPI", "SQL"],
                        "matched_dimensions": ["testing", "database"],
                        "matched_keywords": [],
                        "fit_score": 10,
                    }
                ],
                "primary_project": "InventoryAPI",
                "weak_dimensions": [],
                "role_lens": "engineering_delivery",
            },
        },
        current_fit_dimension="testing",
        current_project_name="InventoryAPI",
        covered_dimensions=["testing"],
    )

    assert result is not None
    assert result.fit_dimension == "database"
    assert "database query design" in result.next_question.lower()


def test_evaluate_answer_relaxes_borderline_rejection(monkeypatch):
    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(
        interview_service,
        "azure_chat_json",
        lambda **_: {
            "answer_acceptable": False,
            "feedback": {
                "strengths": "You addressed the project at a high level.",
                "improvements": "Be more specific about the exact trend and tools used.",
                "example_answer": "A stronger answer would name the trend, the analysis steps, and the impact.",
            },
            "next_question": "Can you explain a specific trend you identified in your analysis and how it impacted decision-making?",
            "next_question_category": "project_based",
            "fit_dimension": "data_analysis_skills",
            "project_name": "data-insights-pipeline",
            "next_action": "retry_same_question",
        },
    )

    result = interview_service.evaluate_answer(
        user_answer=(
            "In the data-insights-pipeline project, I worked with reporting data to identify trends that could "
            "improve visibility into operations and decision-making. I used Python-based analysis workflows and "
            "reporting logic to organize the data, check for inconsistencies, and make the results easier to "
            "interpret through visual outputs."
        ),
        current_question=(
            "Can you describe a specific instance from your data project where you analyzed a dataset to identify "
            "trends and patterns? What tools did you use, and how did you ensure the quality of the data?"
        ),
        job_description="Data Analyst focused on reports, dashboards, SQL, and analysis workflows.",
        interview_context={
            "user_profile": {
                "resume_text": "Built data analysis workflows",
                "project_summaries": ["Created reporting pipelines and visual outputs"],
                "tags": ["analytics"],
                "extracted_skills": ["Python", "SQL", "matplotlib"],
                "repository_history_summary": [],
                "repository_file_evidence": [],
                "collaboration_signals": [],
            },
            "job_readiness_signals": {"strengths": [], "weaknesses": [], "suggestions": []},
            "job_fit_context": {
                "prioritized_dimensions": [
                    {"dimension": "data_analysis_skills", "label": "data analysis skills", "matches": ["trends", "analysis", "data quality"]},
                    {"dimension": "stakeholder_communication", "label": "stakeholder communication", "matches": ["decision-making"]},
                ],
                "relevant_projects": [
                    {
                        "project_name": "data-insights-pipeline",
                        "summary": "Reporting pipeline project",
                        "tech_stack": ["Python", "matplotlib"],
                        "evidence_points": ["Automated reporting", "Data visualization", "Cross-functional insights"],
                        "matched_dimensions": ["data_analysis_skills", "stakeholder_communication"],
                        "matched_keywords": [],
                        "role_hits": ["analytics", "reporting"],
                        "fit_score": 12,
                    }
                ],
                "primary_project": "data-insights-pipeline",
                "weak_dimensions": [],
                "role_lens": "data_analysis",
                "allowed_tools": ["Python", "matplotlib"],
            },
        },
        current_fit_dimension="data_analysis_skills",
        current_project_name="data-insights-pipeline",
    )

    assert result is not None
    assert result.answer_acceptable is True
    assert "on-topic" in result.feedback.strengths.lower()
    assert result.next_action != "retry_same_question"


def test_parse_answer_payload_regrounds_unsupported_example_details():
    payload = {
        "answer_acceptable": True,
        "feedback": {
            "strengths": "You described your testing approach clearly.",
            "improvements": "Add one concrete example.",
            "example_answer": "I used pytest alongside Prometheus metrics and Dockerized smoke tests to validate the API.",
        },
        "next_question": "What tradeoffs did you make?",
        "next_question_category": "project_based",
        "fit_dimension": "testing",
        "project_name": "InventoryAPI",
        "next_action": "advance_dimension",
    }

    result = interview_service._parse_answer_payload(  # type: ignore[attr-defined]
        payload,
        fit_dimension="testing",
        project_name="InventoryAPI",
        interview_context={
            "job_fit_context": {
                "relevant_projects": [
                    {
                        "project_name": "InventoryAPI",
                        "summary": "FastAPI API",
                        "tech_stack": ["FastAPI", "SQL"],
                        "matched_dimensions": ["testing"],
                        "matched_keywords": [],
                        "fit_score": 8,
                    }
                ]
            }
        },
        user_answer="I tested the main endpoint flows and common failure cases.",
    )

    assert result is not None
    assert "prometheus" not in result.feedback.example_answer.lower()
    assert "docker" not in result.feedback.example_answer.lower()


def test_render_prompt_context_exposes_allowed_tools_from_job_description():
    context = {
        "user_profile": {
            "resume_text": "Built dashboards",
            "project_summaries": ["Analytics portal"],
            "tags": ["analytics"],
            "extracted_skills": ["SQL", "JavaScript"],
            "repository_history_summary": [],
            "repository_file_evidence": [],
            "collaboration_signals": [],
        },
        "job_readiness_signals": {"strengths": [], "weaknesses": [], "suggestions": []},
        "job_fit_context": {
            "prioritized_dimensions": [
                {"dimension": "collaboration_skills", "label": "collaboration skills", "matches": ["stakeholder"]},
            ],
            "relevant_projects": [
                {
                    "project_name": "Portal",
                    "summary": "Analytics portal",
                    "tech_stack": ["React", "SQL"],
                    "evidence_points": ["Translated requirements into dashboard tasks"],
                    "matched_dimensions": ["collaboration_skills"],
                    "matched_keywords": [],
                    "fit_score": 6,
                }
            ],
            "primary_project": "Portal",
            "weak_dimensions": [],
            "role_lens": "product_strategy",
            "allowed_tools": ["Jira"],
        },
    }

    prompt_context = interview_service._render_prompt_context(  # type: ignore[attr-defined]
        interview_context=context,
        fit_dimension="collaboration_skills",
        project_name="Portal",
    )

    assert "Jira" in prompt_context["allowed_tools"]
    assert "Translated requirements into dashboard tasks" in prompt_context["allowed_example_points"]


def test_parse_answer_payload_keeps_allowed_tool_details():
    payload = {
        "answer_acceptable": True,
        "feedback": {
            "strengths": "You described how you coordinated priorities clearly.",
            "improvements": "Add one concrete workflow detail.",
            "example_answer": "I kept priorities aligned by documenting tasks in Jira and using regular check-ins to make sure everyone understood the next steps.",
        },
        "next_question": "How did you handle stakeholder tradeoffs?",
        "next_question_category": "project_based",
        "fit_dimension": "collaboration_skills",
        "project_name": "Portal",
        "next_action": "advance_dimension",
    }

    result = interview_service._parse_answer_payload(  # type: ignore[attr-defined]
        payload,
        fit_dimension="collaboration_skills",
        project_name="Portal",
        interview_context={
            "job_fit_context": {
                "relevant_projects": [
                    {
                        "project_name": "Portal",
                        "summary": "Analytics portal",
                        "tech_stack": ["React"],
                        "evidence_points": ["Kept dashboard tasks aligned with stakeholder needs"],
                        "matched_dimensions": ["collaboration_skills"],
                        "matched_keywords": [],
                        "fit_score": 5,
                    }
                ],
                "prioritized_dimensions": [
                    {"dimension": "collaboration_skills", "label": "collaboration skills", "matches": []}
                ],
                "role_lens": "product_strategy",
                "allowed_tools": ["Jira"],
            }
        },
        user_answer="I kept communication clear and aligned tasks with stakeholder needs.",
    )

    assert result is not None
    assert "jira" in result.feedback.example_answer.lower()


def test_derive_job_fit_context_prefers_ui_project_for_ux_role():
    dashboard_project = ProjectReportModel(
        project_name="web-analytics-portal",
        statistic={"primary_language": "JavaScript"},
        showcase_title="Analytics Dashboard",
        showcase_frameworks=["React"],
        showcase_bullet_points=["Improved dashboard clarity", "Supported stakeholder reporting"],
    )
    backend_project = ProjectReportModel(
        project_name="fastapi-orders-service",
        statistic={"primary_language": "Python"},
        showcase_title="Orders API",
        showcase_frameworks=["FastAPI"],
        showcase_bullet_points=["Built order endpoints", "Added backend reliability checks"],
    )

    context = interview_service._derive_job_fit_context(  # type: ignore[attr-defined]
        job_description=(
            "UX Designer role focused on web and mobile products, user needs, interface design, "
            "usability, iteration, and collaboration with product managers and engineers."
        ),
        projects=[dashboard_project, backend_project],
        dimensions=[
            {
                "dimension": "collaboration_experience",
                "label": "cross-functional collaboration",
                "matches": ["product managers", "engineers", "stakeholders", "usability", "design"],
                "priority": 1,
                "reason": "Assess collaboration on user-facing product work.",
                "preferred_question_category": "project_based",
            }
        ],
        readiness_signals={"strengths": [], "weaknesses": [], "suggestions": []},
        role_lens="product_strategy",
    )

    assert context["primary_project"] == "web-analytics-portal"
    assert context["relevant_projects"][0]["project_name"] == "web-analytics-portal"


def test_select_project_for_dimension_validates_model_choice(monkeypatch):
    def fake_azure_chat_json(**kwargs):
        if kwargs.get("schema_name") == interview_service.DEFAULT_INTERVIEW_PROJECT_SCHEMA_NAME:
            return {
                "project_name": "fastapi-orders-service",
                "reason": "Choose the technically strongest project.",
            }
        raise AssertionError("Unexpected schema requested")

    monkeypatch.setattr(interview_service, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(interview_service, "azure_chat_json", fake_azure_chat_json)

    selected = interview_service._select_project_for_dimension(  # type: ignore[attr-defined]
        {
            "job_fit_context": {
                "role_lens": "product_strategy",
                "primary_project": "fastapi-orders-service",
                "relevant_projects": [
                    {
                        "project_name": "fastapi-orders-service",
                        "summary": "Orders API",
                        "tech_stack": ["FastAPI"],
                        "evidence_points": ["Built backend endpoints"],
                        "matched_dimensions": ["user_centered_design"],
                        "role_hits": [],
                        "fit_score": 20,
                    },
                    {
                        "project_name": "web-analytics-portal",
                        "summary": "Analytics dashboard",
                        "tech_stack": ["React"],
                        "evidence_points": ["Improved dashboard clarity for users"],
                        "matched_dimensions": ["user_centered_design"],
                        "role_hits": ["dashboard", "user"],
                        "fit_score": 18,
                    },
                ],
            }
        },
        "user_centered_design",
        job_description=(
            "UX Designer role focused on user needs, usability, interface clarity, and web products."
        ),
    )

    assert selected == "web-analytics-portal"
