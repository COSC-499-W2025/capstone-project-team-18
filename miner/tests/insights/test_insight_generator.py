"""
Unit tests for InsightGenerator and each InsightCalculator.

Tests use a MagicMock as a stand-in for ProjectReport, wiring
get_value() to return controlled statistics so each calculator
can be exercised in isolation.
"""

from unittest.mock import MagicMock

from src.core.insight.insight_generator import (
    ActivityInsightCalculator,
    CollaborationInsightCalculator,
    CommitFocusInsightCalculator,
    InsightGenerator,
    OwnershipInsightCalculator,
    ProjectInsight,
    ReadmeNarrativeInsightCalculator,
    SkillsInsightCalculator,
    WorkPatternInsightCalculator,
)
from src.core.statistic.project_stat_collection import ProjectStatCollection
from src.core.statistic.statistic_models import FileDomain, WeightedSkills


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_report(stat_map: dict | None = None):
    """Return a MagicMock whose get_value() resolves from stat_map.

    Keys should be StatisticTemplate objects (i.e. ProjectStatCollection.*.value).
    """
    report = MagicMock()
    stat_map = stat_map or {}
    report.get_value.side_effect = lambda key: stat_map.get(key)
    return report


# ---------------------------------------------------------------------------
# ProjectInsight dataclass
# ---------------------------------------------------------------------------

def test_project_insight_stores_message():
    insight = ProjectInsight(message="Hello, resume!")
    assert insight.message == "Hello, resume!"


# ---------------------------------------------------------------------------
# ActivityInsightCalculator
# ---------------------------------------------------------------------------

def test_activity_calculator_high_code_contribution():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.CODE.value: 75.0,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert len(insights) >= 1
    assert "75%" in insights[0].message
    assert "code" in insights[0].message.lower()


def test_activity_calculator_moderate_code_contribution():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.CODE.value: 35.0,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "solid code" in insights[0].message.lower()


def test_activity_calculator_high_test_contribution():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.TEST.value: 30.0,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert any("test" in i.message.lower() for i in insights)


def test_activity_calculator_high_design_contribution():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.DESIGN.value: 25.0,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert any("design" in i.message.lower() or "ui" in i.message.lower()
               for i in insights)


def test_activity_calculator_high_doc_contribution():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.DOCUMENTATION.value: 40.0,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert any("documentation" in i.message.lower() for i in insights)


def test_activity_calculator_no_contributions_returns_empty():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: None
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert insights == []


def test_activity_calculator_low_values_produce_no_insights():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.CODE.value: 5.0,
            FileDomain.TEST.value: 2.0,
            FileDomain.DESIGN.value: 1.0,
            FileDomain.DOCUMENTATION.value: 0.5,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert insights == []


def test_activity_calculator_accepts_enum_keys():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.CODE: 80.0,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert len(insights) >= 1


def test_activity_calculator_can_emit_multiple_insights():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.CODE.value: 60.0,
            FileDomain.TEST.value: 30.0,
            FileDomain.DOCUMENTATION.value: 25.0,
        }
    })
    insights = ActivityInsightCalculator().calculate(report)
    assert len(insights) == 3
    assert any("code files" in i.message for i in insights)
    assert any("test files" in i.message for i in insights)
    assert any("documentation" in i.message.lower() for i in insights)


# ---------------------------------------------------------------------------
# OwnershipInsightCalculator
# ---------------------------------------------------------------------------

def test_ownership_calculator_high_ownership():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 85.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "85%" in insights[0].message
    assert "primary contributor" in insights[0].message.lower()


def test_ownership_calculator_moderate_ownership():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 50.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "50%" in insights[0].message


def test_ownership_calculator_low_ownership_returns_empty():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 20.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert insights == []


def test_ownership_calculator_falls_back_to_line_percentage():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: None,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: 75.0,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert len(insights) == 1


def test_ownership_calculator_no_data_returns_empty():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: None,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert insights == []


def test_ownership_calculator_non_group_project_returns_empty():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 95.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: 95.0,
        ProjectStatCollection.IS_GROUP_PROJECT.value: False,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert insights == []


# ---------------------------------------------------------------------------
# CollaborationInsightCalculator
# ---------------------------------------------------------------------------

def test_collaboration_calculator_group_project():
    report = _mock_report({
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
        ProjectStatCollection.TOTAL_AUTHORS.value: 4,
        ProjectStatCollection.COLLABORATION_ROLE.value: None,
        ProjectStatCollection.ROLE_DESCRIPTION.value: None,
    })
    insights = CollaborationInsightCalculator().calculate(report)
    assert any("4 contributors" in i.message for i in insights)


def test_collaboration_calculator_lead_role():
    report = _mock_report({
        ProjectStatCollection.IS_GROUP_PROJECT.value: False,
        ProjectStatCollection.TOTAL_AUTHORS.value: 1,
        ProjectStatCollection.COLLABORATION_ROLE.value: "Tech Lead",
        ProjectStatCollection.ROLE_DESCRIPTION.value: None,
    })
    insights = CollaborationInsightCalculator().calculate(report)
    assert any("Tech Lead" in i.message for i in insights)
    assert any("architectural" in i.message.lower() for i in insights)


def test_collaboration_calculator_role_with_description():
    report = _mock_report({
        ProjectStatCollection.IS_GROUP_PROJECT.value: False,
        ProjectStatCollection.TOTAL_AUTHORS.value: 1,
        ProjectStatCollection.COLLABORATION_ROLE.value: "Contributor",
        ProjectStatCollection.ROLE_DESCRIPTION.value: "Focused on backend API work.",
    })
    insights = CollaborationInsightCalculator().calculate(report)
    assert any("Focused on backend API work." in i.message for i in insights)


def test_collaboration_calculator_no_group_no_role_returns_empty():
    report = _mock_report({
        ProjectStatCollection.IS_GROUP_PROJECT.value: False,
        ProjectStatCollection.TOTAL_AUTHORS.value: 1,
        ProjectStatCollection.COLLABORATION_ROLE.value: None,
        ProjectStatCollection.ROLE_DESCRIPTION.value: None,
    })
    insights = CollaborationInsightCalculator().calculate(report)
    assert insights == []


def test_collaboration_calculator_role_description_without_role():
    report = _mock_report({
        ProjectStatCollection.IS_GROUP_PROJECT.value: False,
        ProjectStatCollection.TOTAL_AUTHORS.value: 1,
        ProjectStatCollection.COLLABORATION_ROLE.value: None,
        ProjectStatCollection.ROLE_DESCRIPTION.value: "Owned backend API integrations and deployment hardening.",
    })
    insights = CollaborationInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "Owned backend API integrations" in insights[0].message


def test_collaboration_calculator_group_project_and_role_emit_both_insights():
    report = _mock_report({
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
        ProjectStatCollection.TOTAL_AUTHORS.value: 5,
        ProjectStatCollection.COLLABORATION_ROLE.value: "Lead Architect",
        ProjectStatCollection.ROLE_DESCRIPTION.value: None,
    })
    insights = CollaborationInsightCalculator().calculate(report)
    assert len(insights) == 2
    assert any("5 contributors" in i.message for i in insights)
    assert any("Lead Architect" in i.message for i in insights)


# ---------------------------------------------------------------------------
# SkillsInsightCalculator
# ---------------------------------------------------------------------------

def test_skills_calculator_top_three_skills():
    skills = [
        WeightedSkills(skill_name="Python", weight=0.9),
        WeightedSkills(skill_name="FastAPI", weight=0.7),
        WeightedSkills(skill_name="SQLModel", weight=0.5),
        WeightedSkills(skill_name="Docker", weight=0.2),
    ]
    report = _mock_report({
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: skills,
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: None,
    })
    insights = SkillsInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "Python" in insights[0].message
    assert "FastAPI" in insights[0].message
    assert "SQLModel" in insights[0].message
    assert "Docker" not in insights[0].message


def test_skills_calculator_single_skill():
    report = _mock_report({
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: [
            WeightedSkills(skill_name="Go", weight=1.0)
        ],
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: None,
    })
    insights = SkillsInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "Go" in insights[0].message


def test_skills_calculator_two_skills():
    report = _mock_report({
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: [
            WeightedSkills(skill_name="React", weight=0.8),
            WeightedSkills(skill_name="TypeScript", weight=0.6),
        ],
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: None,
    })
    insights = SkillsInsightCalculator().calculate(report)
    assert "React and TypeScript" in insights[0].message


def test_skills_calculator_falls_back_to_frameworks():
    report = _mock_report({
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: None,
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: [
            WeightedSkills(skill_name="Django", weight=0.9),
        ],
    })
    insights = SkillsInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "Django" in insights[0].message


def test_skills_calculator_no_skills_returns_empty():
    report = _mock_report({
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: None,
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: None,
    })
    insights = SkillsInsightCalculator().calculate(report)
    assert insights == []


def test_skills_calculator_accepts_dict_items():
    report = _mock_report({
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: [
            {"skill_name": "Rust", "weight": 0.95},
        ],
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: None,
    })
    insights = SkillsInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "Rust" in insights[0].message


def test_skills_calculator_accepts_name_key_and_limits_to_top_three():
    report = _mock_report({
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: None,
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: [
            {"name": "React", "weight": 0.9},
            {"name": "TypeScript", "weight": 0.8},
            {"name": "Vite", "weight": 0.7},
            {"name": "Jest", "weight": 0.1},
        ],
    })
    insights = SkillsInsightCalculator().calculate(report)
    assert len(insights) == 1
    message = insights[0].message
    assert "React" in message and "TypeScript" in message and "Vite" in message
    assert "Jest" not in message


# ---------------------------------------------------------------------------
# ReadmeNarrativeInsightCalculator
# ---------------------------------------------------------------------------

def test_readme_narrative_calculator_returns_top_ranked_candidates():
    report = _mock_report({
        ProjectStatCollection.PROJECT_THEMES.value: ["analytics", "reporting"],
        ProjectStatCollection.PROJECT_TAGS.value: ["dashboard", "kpi"],
        ProjectStatCollection.PROJECT_TONE.value: "Professional",
    })
    insights = ReadmeNarrativeInsightCalculator().calculate(report)
    assert len(insights) == 2
    assert "analytics and reporting" in insights[0].message.lower()
    assert "dashboard and kpi" in insights[1].message.lower()


def test_readme_narrative_calculator_falls_back_to_tags():
    report = _mock_report({
        ProjectStatCollection.PROJECT_THEMES.value: None,
        ProjectStatCollection.PROJECT_TAGS.value: ["automation", "api"],
        ProjectStatCollection.PROJECT_TONE.value: None,
    })
    insights = ReadmeNarrativeInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "automation and api" in insights[0].message.lower()


def test_readme_narrative_calculator_tone_only():
    report = _mock_report({
        ProjectStatCollection.PROJECT_THEMES.value: None,
        ProjectStatCollection.PROJECT_TAGS.value: None,
        ProjectStatCollection.PROJECT_TONE.value: "Educational",
    })
    insights = ReadmeNarrativeInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "educational tone" in insights[0].message.lower()


# ---------------------------------------------------------------------------
# CommitFocusInsightCalculator
# ---------------------------------------------------------------------------

def test_commit_focus_calculator_feature_focus():
    report = _mock_report({
        ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value: {
            "feature": 72.0,
            "docs": 28.0,
        }
    })
    insights = CommitFocusInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "72%" in insights[0].message
    assert "feature" in insights[0].message.lower()


def test_commit_focus_calculator_docs_focus():
    report = _mock_report({
        ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value: {
            "documentation": 60.0,
            "feature": 40.0,
        }
    })
    insights = CommitFocusInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "documentation" in insights[0].message.lower()


def test_commit_focus_calculator_unknown_label_and_case_normalization():
    report = _mock_report({
        ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value: {
            "  Chore ": 51.0,
            "feature": 49.0,
        }
    })
    insights = CommitFocusInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "'chore'" in insights[0].message.lower()
    assert "51%" in insights[0].message


def test_commit_focus_calculator_non_positive_top_weight_returns_empty():
    report = _mock_report({
        ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value: {
            "feature": 0.0,
            "docs": -1.0,
        }
    })
    insights = CommitFocusInsightCalculator().calculate(report)
    assert insights == []


# ---------------------------------------------------------------------------
# WorkPatternInsightCalculator
# ---------------------------------------------------------------------------

def test_work_pattern_calculator_sprint():
    report = _mock_report({
        ProjectStatCollection.WORK_PATTERN.value: "sprint-based"
    })
    insights = WorkPatternInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "sprint" in insights[0].message.lower()


def test_work_pattern_calculator_burst():
    report = _mock_report({
        ProjectStatCollection.WORK_PATTERN.value: "burst"
    })
    insights = WorkPatternInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "burst" in insights[0].message.lower()


def test_work_pattern_calculator_consistent():
    report = _mock_report({
        ProjectStatCollection.WORK_PATTERN.value: "consistent"
    })
    insights = WorkPatternInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "consistent" in insights[0].message.lower()


def test_work_pattern_calculator_unknown_pattern_returns_empty():
    report = _mock_report({
        ProjectStatCollection.WORK_PATTERN.value: "chaotic"
    })
    insights = WorkPatternInsightCalculator().calculate(report)
    assert insights == []


def test_work_pattern_calculator_no_pattern_returns_empty():
    report = _mock_report({
        ProjectStatCollection.WORK_PATTERN.value: None
    })
    insights = WorkPatternInsightCalculator().calculate(report)
    assert insights == []


def test_work_pattern_calculator_is_case_insensitive():
    report = _mock_report({
        ProjectStatCollection.WORK_PATTERN.value: "CONSISTENT"
    })
    insights = WorkPatternInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "consistent" in insights[0].message.lower()


# ---------------------------------------------------------------------------
# InsightGenerator
# ---------------------------------------------------------------------------

def test_insight_generator_runs_all_calculators_by_default():
    report = _mock_report({
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value: {
            FileDomain.CODE.value: 80.0,
        },
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 75.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
        ProjectStatCollection.IS_GROUP_PROJECT.value: True,
        ProjectStatCollection.TOTAL_AUTHORS.value: 3,
        ProjectStatCollection.COLLABORATION_ROLE.value: None,
        ProjectStatCollection.ROLE_DESCRIPTION.value: None,
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value: [
            WeightedSkills(skill_name="Python", weight=1.0)
        ],
        ProjectStatCollection.PROJECT_FRAMEWORKS.value: None,
        ProjectStatCollection.WORK_PATTERN.value: "consistent",
    })
    insights = InsightGenerator.generate(report)
    assert len(insights) > 0
    assert all(isinstance(i, ProjectInsight) for i in insights)


def test_insight_generator_with_specific_calculators():
    report = _mock_report({
        ProjectStatCollection.WORK_PATTERN.value: "sprint-based",
    })
    insights = InsightGenerator.generate(report, requested_classes=[
                                         WorkPatternInsightCalculator])
    assert len(insights) == 1
    assert "sprint" in insights[0].message.lower()


def test_insight_generator_empty_requested_classes_returns_empty():
    report = _mock_report()
    insights = InsightGenerator.generate(report, requested_classes=[])
    assert insights == []


def test_insight_generator_returns_empty_when_no_stats():
    report = _mock_report()  # all get_value() calls return None
    insights = InsightGenerator.generate(report)
    assert isinstance(insights, list)


def test_insight_generator_preserves_master_list_order_for_requested_classes():
    report = _mock_report({
        ProjectStatCollection.PROJECT_THEMES.value: ["analytics"],
        ProjectStatCollection.PROJECT_TONE.value: "Professional",
        ProjectStatCollection.WORK_PATTERN.value: "consistent",
    })
    insights = InsightGenerator.generate(
        report,
        requested_classes=[WorkPatternInsightCalculator, ReadmeNarrativeInsightCalculator],
    )
    assert len(insights) == 3
    assert "project narrative" in insights[0].message.lower()
    assert "tone" in insights[1].message.lower()
    assert "consistent" in insights[2].message.lower()
