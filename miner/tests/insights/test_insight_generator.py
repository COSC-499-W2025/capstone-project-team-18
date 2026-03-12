"""
Unit tests for InsightGenerator and each InsightCalculator.

Tests use a MagicMock as a stand-in for ProjectReport, wiring
get_value() to return controlled statistics so each calculator
can be exercised in isolation.
"""

import pytest
from unittest.mock import MagicMock

from src.core.insight.insight_generator import (
    ActivityInsightCalculator,
    CollaborationInsightCalculator,
    InsightGenerator,
    OwnershipInsightCalculator,
    ProjectInsight,
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
    assert any("design" in i.message.lower() or "ui" in i.message.lower() for i in insights)


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


# ---------------------------------------------------------------------------
# OwnershipInsightCalculator
# ---------------------------------------------------------------------------

def test_ownership_calculator_high_ownership():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 85.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "85%" in insights[0].message
    assert "primary contributor" in insights[0].message.lower()


def test_ownership_calculator_moderate_ownership():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 50.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert len(insights) == 1
    assert "50%" in insights[0].message


def test_ownership_calculator_low_ownership_returns_empty():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 20.0,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert insights == []


def test_ownership_calculator_falls_back_to_line_percentage():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: None,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: 75.0,
    })
    insights = OwnershipInsightCalculator().calculate(report)
    assert len(insights) == 1


def test_ownership_calculator_no_data_returns_empty():
    report = _mock_report({
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: None,
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value: None,
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
    insights = InsightGenerator.generate(report, requested_classes=[WorkPatternInsightCalculator])
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
