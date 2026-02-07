import os
from datetime import date

import pytest

from src.core.report import UserReport, ProjectReport
from src.core.statistic import (
    StatisticIndex,
    Statistic,
    UserStatCollection,
    ProjectStatCollection,
    WeightedSkills,
    CodingLanguage,
)
from src.core.portfolio.builder.concrete_builders import UserSummarySectionBuilder


def _make_project_report(
    tmp_path,
    *,
    role=None,
    cadence=None,
    commit_focus=None,
    frameworks=None,
    themes=None,
    tone=None,
):
    stats = StatisticIndex()

    if role is not None:
        stats.add(Statistic(ProjectStatCollection.COLLABORATION_ROLE.value, role))
    if cadence is not None:
        stats.add(Statistic(ProjectStatCollection.WORK_PATTERN.value, cadence))
    if commit_focus is not None:
        stats.add(Statistic(ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value, commit_focus))
    if frameworks is not None:
        stats.add(Statistic(ProjectStatCollection.PROJECT_FRAMEWORKS.value, frameworks))
    if themes is not None:
        stats.add(Statistic(ProjectStatCollection.PROJECT_THEMES.value, themes))
    if tone is not None:
        stats.add(Statistic(ProjectStatCollection.PROJECT_TONE.value, tone))

    return ProjectReport(
        file_reports=[],
        project_path=str(tmp_path),
        project_name="ExampleProject",
        statistics=stats,
    )


def _make_user_report(project_reports, *, start_date=None, end_date=None):
    user_stats = StatisticIndex()
    user_stats.add(
        Statistic(
            UserStatCollection.USER_CODING_LANGUAGE_RATIO.value,
            {
                CodingLanguage.PYTHON: 0.7,
                CodingLanguage.SQL: 0.2,
                CodingLanguage.JAVA: 0.1,
            },
        )
    )
    user_stats.add(
        Statistic(
            UserStatCollection.USER_SKILLS.value,
            [
                WeightedSkills("Python", 0.5),
                WeightedSkills("SQL", 0.3),
                WeightedSkills("Power BI", 0.2),
            ],
        )
    )
    if start_date is not None:
        user_stats.add(
            Statistic(UserStatCollection.USER_START_DATE.value, start_date)
        )
    if end_date is not None:
        user_stats.add(
            Statistic(UserStatCollection.USER_END_DATE.value, end_date)
        )

    return UserReport(
        project_reports=project_reports,
        report_name="TestUser",
        statistics=user_stats,
    )


def test_summary_section_uses_ml_when_available(tmp_path, monkeypatch):
    project = _make_project_report(
        tmp_path,
        role="core_contributor",
        cadence="consistent",
        commit_focus={"feature": 60, "docs": 40},
        frameworks=[WeightedSkills("FastAPI", 1.0)],
        themes=["analytics"],
    )
    report = _make_user_report([project])

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    def fake_generate_signature(_facts):
        return (
            "Data-driven developer with strong analytics experience, focused on deriving insights from data and "
            "improving software delivery outcomes through clear measurement. Skilled in Python, SQL, and "
            "dashboarding tools, with proven ability to automate reporting and communicate findings to "
            "technical and non-technical stakeholders."
        )

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        fake_generate_signature,
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert "Summary" in builder.section_title
    assert "Data-driven developer" in blocks[0].current_content.render()

    # Verify key facts passed to generator
    assert captured_facts["role"] == "core_contributor"
    assert captured_facts["cadence"] == "consistent"
    assert "Python" in captured_facts["top_skills"]
    assert "activities" in captured_facts
    assert "emerging" in captured_facts


def test_summary_section_falls_back_on_invalid_summary(tmp_path, monkeypatch):
    project = _make_project_report(tmp_path, role="leader", cadence="burst")
    report = _make_user_report([project])

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: "Too short.",
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert blocks == []


def test_summary_section_skips_when_ml_required_and_missing(tmp_path, monkeypatch):
    project = _make_project_report(tmp_path, role="solo")
    report = _make_user_report([project])

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: None,
    )

    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    try:
        builder = UserSummarySectionBuilder()
        blocks = builder.create_blocks(report)
        assert blocks == []
    finally:
        monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)


def test_summary_section_handles_missing_data(tmp_path, monkeypatch):
    project = _make_project_report(tmp_path)
    report = UserReport(
        project_reports=[project],
        report_name="TestUser",
        statistics=StatisticIndex(),
    )

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: None,
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    # With no data and no ML, summary should be omitted
    assert blocks == []


def test_summary_section_no_projects_no_stats(monkeypatch):
    report = UserReport(
        project_reports=[],
        report_name="EmptyUser",
        statistics=StatisticIndex(),
    )

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: None,
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)
    assert blocks == []


def test_summary_section_aggregates_tools_across_projects(tmp_path, monkeypatch):
    project_a = _make_project_report(
        tmp_path,
        frameworks=[WeightedSkills("FastAPI", 1.0), WeightedSkills("SQLAlchemy", 0.5)],
    )
    project_b = _make_project_report(
        tmp_path,
        frameworks=[WeightedSkills("FastAPI", 0.8), WeightedSkills("Pandas", 0.9)],
    )

    report = _make_user_report([project_a, project_b])

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Experienced developer using FastAPI and Pandas to build reliable services and data tools. "
            "Skilled in Python with a focus on data-backed development and pragmatic engineering outcomes."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    tools = captured_facts.get("tools", [])
    assert "FastAPI" in tools
    assert "Pandas" in tools


def test_summary_section_commit_focus_aggregates(tmp_path, monkeypatch):
    project_a = _make_project_report(
        tmp_path,
        commit_focus={"feature": 60, "docs": 40},
    )
    project_b = _make_project_report(
        tmp_path,
        commit_focus={"feature": 20, "fix": 80},
    )
    report = _make_user_report([project_a, project_b])

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Contributor focused on feature delivery and product improvements across multiple codebases. "
            "Strong in Python and Java with experience building dependable systems and maintainable services."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert captured_facts["commit_focus"] in {"feature", "fix", "docs"}


def test_summary_section_focus_inference_uses_skills_and_tools(tmp_path, monkeypatch):
    project = _make_project_report(
        tmp_path,
        frameworks=[WeightedSkills("Power BI", 1.0), WeightedSkills("Pandas", 0.7)],
    )
    report = _make_user_report([project])

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Data-focused developer with experience in analytics, reporting, and operational insights. "
            "Skilled in Python and SQL with exposure to Power BI and practical dashboard workflows."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert captured_facts["focus"] == "Analytics"


def test_summary_section_focus_inference_uses_skillmapper_keywords(tmp_path, monkeypatch):
    # "statsmodels" is sourced from SkillMapper indicators (Data Analytics).
    project = _make_project_report(
        tmp_path,
        frameworks=[WeightedSkills("statsmodels", 1.0)],
    )
    report = _make_user_report([project])

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Data-focused developer with practical analytics experience, strong problem framing, and consistent delivery habits. "
            "Skilled in Python and SQL with evidence-driven reporting workflows that improve decision quality and communication."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert captured_facts["focus"] == "Analytics"


def test_summary_section_emerging_signals_use_skillmapper_keywords(tmp_path, monkeypatch):
    # "huggingface" is from SkillMapper ML packages and should surface as emerging.
    project = _make_project_report(
        tmp_path,
        frameworks=[WeightedSkills("huggingface", 1.0)],
    )
    report = _make_user_report([project])

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Machine-learning oriented developer with practical experience building model-backed workflows and experimentation cycles. "
            "Strong in Python and SQL with reliable delivery habits and clear technical communication."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert any(
        signal in captured_facts["emerging"]
        for signal in {"Generative AI", "Machine Learning"}
    )


def test_summary_section_infers_experience_stage_from_timeline(tmp_path, monkeypatch):
    project = _make_project_report(
        tmp_path,
        role="leader",
        frameworks=[WeightedSkills("FastAPI", 1.0)],
        tone="Professional",
    )
    report = _make_user_report(
        [project],
        start_date=date(2019, 1, 1),
        end_date=date(2026, 1, 1),
    )

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Experienced software engineer with practical experience in backend services and delivery quality. "
            "Strong in Python and FastAPI with a track record of dependable implementation and communication."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert captured_facts["experience_stage"] == "early-career"


def test_summary_stage_not_overstated_for_single_old_project(tmp_path, monkeypatch):
    project = _make_project_report(
        tmp_path,
        role="core_contributor",
        frameworks=[WeightedSkills("FastAPI", 1.0)],
        tone="Professional",
    )
    report = _make_user_report(
        [project],
        start_date=date(2017, 1, 1),
        end_date=date(2026, 1, 1),
    )

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Engineer with practical backend experience and clear delivery focus across technical initiatives. "
            "Strong in Python and SQL with an emphasis on reliability and maintainable implementation."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert captured_facts["experience_stage"] != "experienced"


def test_summary_stage_uses_professional_tone_for_multi_project_history(tmp_path, monkeypatch):
    projects = [
        _make_project_report(
            tmp_path,
            role="leader" if idx == 0 else "core_contributor",
            frameworks=[WeightedSkills("FastAPI", 1.0)],
            tone="Professional",
        )
        for idx in range(5)
    ]
    report = _make_user_report(
        projects,
        start_date=date(2019, 1, 1),
        end_date=date(2026, 1, 1),
    )

    captured_facts = {}

    def fake_build_signature_facts(**kwargs):
        captured_facts.update(kwargs)
        return {"mock": "facts"}

    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.build_signature_facts",
        fake_build_signature_facts,
    )
    monkeypatch.setattr(
        "src.core.portfolio.builder.concrete_builders.generate_signature",
        lambda _facts: (
            "Experienced engineer with a track record of delivering production-oriented backend services and measurable improvements. "
            "Strong in Python and SQL with consistent execution and clear collaboration across technical contexts."
        ),
    )

    builder = UserSummarySectionBuilder()
    blocks = builder.create_blocks(report)

    assert len(blocks) == 1
    assert captured_facts["experience_stage"] == "experienced"
