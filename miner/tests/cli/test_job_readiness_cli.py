from __future__ import annotations

from datetime import date, datetime

from sqlmodel import Session

from src.database.api.models import FileReportModel, ProjectReportModel, ResumeItemModel, ResumeModel
from src.interface.cli import cli_service_handler


def _insert_project(blank_db, name: str) -> None:
    with Session(blank_db) as session:
        project = ProjectReportModel(
            project_name=name,
            statistic={"commits": 5},
            created_at=datetime(2026, 3, 1, 12, 0, 0),
            last_updated=datetime(2026, 3, 2, 12, 0, 0),
            analyzed_count=1,
            showcase_title=f"{name} title",
            showcase_frameworks=["FastAPI"],
            showcase_bullet_points=["Built APIs"],
        )
        project.file_reports = [
            FileReportModel(
                project_name=name,
                file_path="api/app.py",
                is_info_file=False,
                statistic={"lines": 10},
            )
        ]
        session.add(project)
        session.commit()


def _insert_resume(blank_db, resume_id: int, project_name: str) -> None:
    with Session(blank_db) as session:
        resume = ResumeModel(
            id=resume_id,
            email="candidate@example.com",
            github="candidate",
            skills=["Python"],
            created_at=datetime(2026, 3, 3, 12, 0, 0),
            last_updated=datetime(2026, 3, 3, 12, 0, 0),
        )
        resume.items = [
            ResumeItemModel(
                id=resume_id,
                resume_id=resume_id,
                project_name=project_name,
                title="Backend Developer",
                frameworks=["FastAPI"],
                bullet_points=["Built APIs"],
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
            )
        ]
        session.add(resume)
        session.commit()


def test_list_project_names_for_cli(blank_db, monkeypatch):
    _insert_project(blank_db, "BProject")
    _insert_project(blank_db, "AProject")

    monkeypatch.setattr(cli_service_handler, "get_engine", lambda: blank_db)

    assert cli_service_handler.list_project_names_for_cli() == ["AProject", "BProject"]


def test_analyze_job_readiness_cli_uses_latest_resume_when_available(blank_db, monkeypatch):
    _insert_project(blank_db, "APIProject")
    _insert_resume(blank_db, 1, "APIProject")
    captured = {}

    def fake_run_job_readiness_analysis(*, job_description, user_profile, max_attempts=2):
        captured["job_description"] = job_description
        captured["user_profile"] = user_profile
        return {"not": "used"}

    monkeypatch.setattr(cli_service_handler, "get_engine", lambda: blank_db)
    monkeypatch.setattr(cli_service_handler, "run_job_readiness_analysis", fake_run_job_readiness_analysis)

    result, user_profile, debug_info = cli_service_handler.analyze_job_readiness_cli(
        job_description="Backend engineer with API experience.",
    )

    assert result == {"not": "used"}
    assert user_profile == captured["user_profile"]
    assert debug_info["evidence_source"] == "latest_resume"
    assert debug_info["resume_id"] == 1
    assert captured["job_description"] == "Backend engineer with API experience."
    assert "candidate@example.com" in captured["user_profile"]["resume_text"]
    assert "Built APIs" in captured["user_profile"]["resume_text"]
    assert captured["user_profile"]["project_summaries"]


def test_analyze_job_readiness_cli_falls_back_to_all_projects(blank_db, monkeypatch):
    _insert_project(blank_db, "APIProject")
    captured = {}

    def fake_run_job_readiness_analysis(*, job_description, user_profile, max_attempts=2):
        captured["user_profile"] = user_profile
        return {"fallback": True}

    monkeypatch.setattr(cli_service_handler, "get_engine", lambda: blank_db)
    monkeypatch.setattr(cli_service_handler, "run_job_readiness_analysis", fake_run_job_readiness_analysis)

    result, user_profile, debug_info = cli_service_handler.analyze_job_readiness_cli(
        job_description="Backend engineer with API experience.",
    )

    assert result == {"fallback": True}
    assert user_profile == captured["user_profile"]
    assert debug_info["evidence_source"] == "all_projects"
    assert debug_info["resume_id"] is None
    assert debug_info["project_names"] == ["APIProject"]
    assert captured["user_profile"]["resume_text"] is None
    assert captured["user_profile"]["project_summaries"]
