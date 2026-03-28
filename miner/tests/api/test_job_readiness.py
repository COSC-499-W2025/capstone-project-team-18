import importlib

import pytest

from src.services.job_readiness_service import JobReadinessAnalysisOutcome, JobReadinessResult

job_readiness_module = importlib.import_module("src.interface.api.routers.job_readiness")


@pytest.fixture(autouse=True)
def enable_ml(monkeypatch):
    monkeypatch.setattr(job_readiness_module, "ml_extraction_allowed", lambda session: True)


def test_job_readiness_returns_specific_configuration_error(client, monkeypatch):
    monkeypatch.setattr(
        job_readiness_module,
        "build_user_profile",
        lambda session, resume_id, project_names, user_profile_input: {"resume_text": "resume evidence"},
    )
    monkeypatch.setattr(
        job_readiness_module,
        "analyze_job_readiness_with_diagnostics",
        lambda job_description, user_profile: JobReadinessAnalysisOutcome(
            result=None,
            error_message="Job readiness analysis is unavailable because Azure OpenAI is not fully configured. Missing: AZURE_OPENAI_API_KEY.",
        ),
    )

    response = client.post(
        "/job-readiness/analyze",
        json={"job_description": "Business analyst intern", "project_names": []},
    )

    assert response.status_code == 503
    assert response.json() == {
        "error_code": "AI_SERVICE_UNAVAILABLE",
        "message": "Job readiness analysis is unavailable because Azure OpenAI is not fully configured. Missing: AZURE_OPENAI_API_KEY.",
    }


def test_job_readiness_returns_successful_result(client, monkeypatch):
    monkeypatch.setattr(
        job_readiness_module,
        "build_user_profile",
        lambda session, resume_id, project_names, user_profile_input: {"resume_text": "resume evidence"},
    )
    monkeypatch.setattr(
        job_readiness_module,
        "analyze_job_readiness_with_diagnostics",
        lambda job_description, user_profile: JobReadinessAnalysisOutcome(
            result=JobReadinessResult.model_validate(
                {
                    "fit_score": 81,
                    "summary": "Strong communication and analysis fit.",
                    "strengths": [{"item": "Requirements gathering", "reason": "Resume evidence shows stakeholder-facing work.", "rank": 1}],
                    "weaknesses": [{"item": "Dashboard tooling", "reason": "Limited evidence of reporting tools.", "rank": 1}],
                    "suggestions": [
                        {
                            "item": "Create a reporting dashboard case study",
                            "reason": "This would add direct analytics evidence.",
                            "priority": 1,
                            "action_type": "create",
                            "resource_name": "Portfolio",
                            "resource_type": "artifact",
                            "resource_hint": "Include metrics and stakeholder outcomes.",
                        }
                    ],
                }
            )
        ),
    )

    response = client.post(
        "/job-readiness/analyze",
        json={"job_description": "Business analyst intern", "project_names": []},
    )

    assert response.status_code == 200
    assert response.json()["fit_score"] == 81
