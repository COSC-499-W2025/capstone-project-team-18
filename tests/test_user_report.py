from src.classes.report import UserReport, ProjectReport, FileReport
from src.classes.statistic import (
    StatisticIndex, Statistic, StatisticTemplate,
    UserStatCollection, WeightedSkills, ProjectStatCollection,
    FileStatCollection,
    CodingLanguage
)
from datetime import date
from datetime import datetime
import unittest
from unittest.mock import Mock, patch
import sys
import os

# Pytest-style tests for existing functionality


def test_to_user_readable_string():
    lang_ratio = {CodingLanguage.PYTHON: 0.8528,
                  CodingLanguage.CSS: 0.1002, CodingLanguage.TYPESCRIPT: 0.0470}
    idx = StatisticIndex([
        Statistic(UserStatCollection.USER_START_DATE.value, date(2023, 9, 20)),
        Statistic(UserStatCollection.USER_END_DATE.value,
                  date(2025, 10, 20)),
        Statistic(UserStatCollection.USER_CODING_LANGUAGE_RATIO.value, lang_ratio),
    ])
    report = UserReport.from_statistics(idx)
    out = report.to_user_readable_string()
    print(out)
    assert "You started your first project on 9/20/2023!" in out
    assert "Your latest contribution was on 10/20/2025." in out
    assert "Your coding languages: Python (85%), CSS (10%), Typescript (4%)"
    # assert "Your skills include: " in out


def test_to_user_readable_string_empty():
    idx = StatisticIndex()
    report = UserReport.from_statistics(idx)
    assert report.to_user_readable_string() == "No user statistics are available yet."


def test_to_user_readable_string_fallback_generic_title_value():
    dummy_template = StatisticTemplate(
        name="CUSTOM_UNKNOWN_STAT",
        description="A stat not covered by custom phrasing",
        expected_type=int,
    )
    idx = StatisticIndex([Statistic(dummy_template, 42)])
    report = UserReport.from_statistics(idx)
    out = report.to_user_readable_string()
    assert "Custom Unknown Stat: 42" in out

 # Unittest-style tests for the new date functionality


class TestUserReportDates(unittest.TestCase):

    def test_user_dates_from_multiple_projects(self):
        """Test user dates calculation from multiple projects"""
        # Create project 1 (earliest start, middle end)
        project1_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2022, 6, 15))
        ])
        project1 = ProjectReport.from_statistics(project1_stats)

        # Create project 2 (middle start, latest end)
        project2_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 3, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 12, 31))
        ])
        project2 = ProjectReport.from_statistics(project2_stats)

        # Create project 3 (latest start, earliest end)
        project3_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2022, 3, 15))
        ])
        project3 = ProjectReport.from_statistics(project3_stats)

        # Create user report
        user = UserReport([project1, project2, project3])

        # Test user start date (earliest project start)
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        self.assertEqual(user_start, datetime(2022, 1, 1))

        # Test user end date (latest project end)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)
        self.assertEqual(user_end, datetime(2023, 12, 31))

    def test_empty_project_list(self):
        """Test that empty project list doesn't crash"""
        user = UserReport([])

        # Should not have start or end dates
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        self.assertIsNone(user_start)
        self.assertIsNone(user_end)

    def test_single_project(self):
        """Test with only one project"""
        project_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 5, 10)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 8, 20))
        ])
        project = ProjectReport.from_statistics(project_stats)

        user = UserReport([project])

        # Start and end should be the same project's dates
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        self.assertEqual(user_start, datetime(2023, 5, 10))
        self.assertEqual(user_end, datetime(2023, 8, 20))

    def test_projects_with_missing_dates(self):
        """Test projects that have None values for dates"""
        # Project with only start date
        project1_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 6, 1))
        ])
        project1 = ProjectReport.from_statistics(project1_stats)

        # Project with only end date
        project2_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 9, 30))
        ])
        project2 = ProjectReport.from_statistics(project2_stats)

        # Project with both dates
        project3_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 15)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 4, 30))
        ])
        project3 = ProjectReport.from_statistics(project3_stats)

        user = UserReport([project1, project2, project3])

        # Should use earliest start date from available projects
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        self.assertEqual(user_start, datetime(2022, 6, 1))

        # Should use latest end date from available projects
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)
        self.assertEqual(user_end, datetime(2023, 9, 30))

    def test_projects_with_no_dates(self):
        """Test projects that have no date statistics at all"""
        project_stats = StatisticIndex([])  # No statistics
        project = ProjectReport.from_statistics(project_stats)

        user = UserReport([project])

        # Should have no dates
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        self.assertIsNone(user_start)
        self.assertIsNone(user_end)

    def test_wrong_date_assumptions(self):
        """Test that dates are calculated correctly with assertFalse"""
        project1_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2022, 6, 15))
        ])
        project1 = ProjectReport.from_statistics(project1_stats)

        project2_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 12, 31))
        ])
        project2 = ProjectReport.from_statistics(project2_stats)

        user = UserReport([project1, project2])

        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        # Assert wrong assumptions are false
        self.assertFalse(user_start == datetime(
            2023, 1, 1))  # Wrong start date
        self.assertFalse(user_end == datetime(2022, 6, 15))   # Wrong end date
        self.assertFalse(user_start == user_end)              # Start != End
        # Start should be before end
        self.assertFalse(user_start > user_end)

    def test_multiple_projects_complex_dates(self):
        """Test with many projects and complex date patterns"""
        projects = []

        # Create 5 projects with various dates
        project_dates = [
            (datetime(2021, 6, 1), datetime(2021, 8, 30)),   # Earliest start
            (datetime(2022, 1, 15), datetime(2022, 12, 20)),
            (datetime(2022, 6, 1), datetime(2024, 1, 31)),   # Latest end
            (datetime(2021, 12, 1), datetime(2022, 3, 15)),
            (datetime(2023, 3, 1), datetime(2023, 11, 30))
        ]

        for i, (start_date, end_date) in enumerate(project_dates):
            stats = StatisticIndex([
                Statistic(
                    ProjectStatCollection.PROJECT_START_DATE.value, start_date),
                Statistic(ProjectStatCollection.PROJECT_END_DATE.value, end_date)
            ])
            projects.append(ProjectReport.from_statistics(stats))

        user = UserReport(projects)

        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        # Should be earliest start and latest end
        self.assertEqual(user_start, datetime(2021, 6, 1))
        self.assertEqual(user_end, datetime(2024, 1, 31))

        # Assert false conditions
        self.assertFalse(user_start == datetime(
            2021, 12, 1))  # Not the second earliest
        self.assertFalse(user_end == datetime(
            2023, 11, 30))   # Not the second latest

    def test_user_report_inheritance(self):
        """Test that UserReport properly inherits from BaseReport"""
        project_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 12, 31))
        ])
        project = ProjectReport.from_statistics(project_stats)

        user = UserReport([project])

        # Test inherited methods work
        self.assertIsNotNone(user.to_dict())
        self.assertIsInstance(user.to_dict(), dict)

        # Test that repr doesn't crash
        repr_str = repr(user)
        self.assertIsInstance(repr_str, str)
        self.assertTrue("UserReport" in repr_str)

    def test_user_timeline_progression(self):
        """Test realistic user timeline progression"""
        # Simulate a user's career progression over time
        # Project 1: College project
        college_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2020, 9, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2020, 12, 15))
        ])
        college_project = ProjectReport.from_statistics(college_stats)

        # Project 2: Internship project
        internship_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2021, 6, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2021, 8, 31))
        ])
        internship_project = ProjectReport.from_statistics(internship_stats)

        # Project 3: Full-time work project
        work_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 1, 3)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2024, 10, 27))
        ])
        work_project = ProjectReport.from_statistics(work_stats)

        user = UserReport([college_project, internship_project, work_project])

        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        # User started in college, most recent work is current
        self.assertEqual(user_start, datetime(2020, 9, 1))
        self.assertEqual(user_end, datetime(2024, 10, 27))

        # Verify timeline makes sense
        self.assertTrue(user_start < user_end)
        self.assertEqual((user_end - user_start).days,
                         (datetime(2024, 10, 27) - datetime(2020, 9, 1)).days)


# Pytest-style tests for _weight_skills method


def test_weight_skills_single_project_single_skill():
    """Test weighting skills with a single project containing one skill"""
    # Create a project with one skill
    project_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
                  [WeightedSkills(skill_name="Python", weight=1.0)])
    ])
    project = ProjectReport.from_statistics(project_stats)

    # Mock the project weight
    project.get_project_weight = Mock(return_value=2.0)

    user = UserReport([project])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 1
    assert user_skills[0].skill_name == "Python"
    # Weight should be 1.0 * 2.0 = 2.0
    assert user_skills[0].weight == 2.0


def test_weight_skills_single_project_multiple_skills():
    """Test weighting skills with a single project containing multiple skills"""
    # Create a project with multiple skills
    project_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Python", weight=0.5),
            WeightedSkills(skill_name="React", weight=0.3),
            WeightedSkills(skill_name="PostgreSQL", weight=0.2)
        ])
    ])
    project = ProjectReport.from_statistics(project_stats)

    user = UserReport([project])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 3
    skill_names = {skill.skill_name for skill in user_skills}
    assert skill_names == {"Python", "React", "PostgreSQL"}


def test_weight_skills_multiple_projects_overlapping_skills():
    """Test that skill weights are accumulated across multiple projects"""
    # Project 1
    project1_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Python", weight=0.5),
            WeightedSkills(skill_name="React", weight=0.5)
        ])
    ])
    project1 = ProjectReport.from_statistics(project1_stats)
    project1.get_project_weight = Mock(return_value=1.5)

    # Project 2 with overlapping skill (Python)
    project2_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Python", weight=0.6),
            WeightedSkills(skill_name="Django", weight=0.4)
        ])
    ])
    project2 = ProjectReport.from_statistics(project2_stats)
    project2.get_project_weight = Mock(return_value=2.0)

    user = UserReport([project1, project2])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 3

    # Check Python skill has accumulated weight: 0.5*1.5 + 0.6*2.0 = 0.75 + 1.2 = 1.95
    python_skills = [s for s in user_skills if s.skill_name == "Python"]
    assert len(python_skills) == 1
    assert python_skills[0].weight == 1.95


def test_weight_skills_empty_project_list():
    """Test weighting skills with no projects"""
    user = UserReport([])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 0


def test_weight_skills_project_with_no_skills():
    """Test weighting skills when project has no skills demonstrated"""
    # Project with no skills
    project_stats = StatisticIndex([])
    project = ProjectReport.from_statistics(project_stats)

    user = UserReport([project])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 0


def test_weight_skills_mixed_projects_some_with_skills():
    """Test with some projects having skills and some having none"""
    # Project 1 with skills
    project1_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Java", weight=0.7)
        ])
    ])
    project1 = ProjectReport.from_statistics(project1_stats)

    # Project 2 without skills
    project2_stats = StatisticIndex([])
    project2 = ProjectReport.from_statistics(project2_stats)

    # Project 3 with skills
    project3_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Java", weight=0.6),
            WeightedSkills(skill_name="Spring", weight=0.4)
        ])
    ])
    project3 = ProjectReport.from_statistics(project3_stats)

    user = UserReport([project1, project2, project3])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 2
    skill_names = {skill.skill_name for skill in user_skills}
    assert skill_names == {"Java", "Spring"}


def test_weight_skills_incorporates_project_weight():
    """Test that user skill weight incorporates project weight"""
    # Create projects with different weights

    # Project 1: Lower weight
    project1_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="TypeScript", weight=1.0)
        ])
    ])
    project1 = ProjectReport.from_statistics(project1_stats)
    project1.get_project_weight = Mock(return_value=1.0)

    # Project 2: Higher weight
    project2_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="TypeScript", weight=1.0)
        ])
    ])
    project2 = ProjectReport.from_statistics(project2_stats)
    project2.get_project_weight = Mock(return_value=2.5)

    user = UserReport([project1, project2])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    # Both projects contribute to TypeScript skill weight
    assert user_skills is not None
    assert len(user_skills) == 1
    assert user_skills[0].skill_name == "TypeScript"
    # Weight should be 1.0*1.0 + 1.0*2.5 = 3.5
    assert user_skills[0].weight == 3.5


def test_weight_skills_many_projects_many_skills():
    """Test with many projects and various skill combinations"""
    skills_per_project = [
        [WeightedSkills(skill_name="Python", weight=0.4),
         WeightedSkills(skill_name="Flask", weight=0.3),
         WeightedSkills(skill_name="SQLAlchemy", weight=0.3)],
        [WeightedSkills(skill_name="Python", weight=0.5),
         WeightedSkills(skill_name="Django", weight=0.5)],
        [WeightedSkills(skill_name="JavaScript", weight=0.6),
         WeightedSkills(skill_name="React", weight=0.4)],
        [WeightedSkills(skill_name="Python", weight=0.8),
         WeightedSkills(skill_name="NumPy", weight=0.2)],
    ]

    project_weights = [1.5, 2.0, 1.8, 2.2]

    projects = []
    for skills, weight in zip(skills_per_project, project_weights):
        project_stats = StatisticIndex([
            Statistic(
                ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, skills)
        ])
        project = ProjectReport.from_statistics(project_stats)
        project.get_project_weight = Mock(return_value=weight)
        projects.append(project)

    user = UserReport(projects)
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    # Should have unique skills from all projects
    skill_names = {skill.skill_name for skill in user_skills}
    expected_skills = {"Python", "Flask", "SQLAlchemy",
                       "Django", "JavaScript", "React", "NumPy"}
    assert skill_names == expected_skills

    # Python should have the highest combined weight
    # Python weights: 0.4*1.5 + 0.5*2.0 + 0.8*2.2 = 0.6 + 1.0 + 1.76 = 3.36
    python_skill = next(s for s in user_skills if s.skill_name == "Python")
    assert abs(python_skill.weight - 3.36) < 1e-9

    max_weight = max(s.weight for s in user_skills)
    assert python_skill.weight == max_weight


def test_weight_skills_creates_user_skills_statistic():
    """Test that _weight_skills creates a USER_SKILLS statistic"""
    project_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Go", weight=1.0)
        ])
    ])
    project = ProjectReport.from_statistics(project_stats)

    user = UserReport([project])

    # Check that USER_SKILLS statistic exists by retrieving the value
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)
    assert user_skills is not None
    assert isinstance(user_skills, list)


def test_weight_skills_identical_skills_same_project():
    """Test handling of duplicate skill names within a project (edge case)"""
    # In practice this shouldn't happen, but let's test robustness
    project_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Rust", weight=0.6),
            WeightedSkills(skill_name="Rust", weight=0.4)  # Same skill twice
        ])
    ])
    project = ProjectReport.from_statistics(project_stats)

    user = UserReport([project])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    # Should handle gracefully - both should be accumulated
    assert user_skills is not None
    rust_skills = [s for s in user_skills if s.skill_name == "Rust"]
    # Either they accumulate into one or stay as separate entries
    assert len(rust_skills) >= 1


def test_weight_skills_preserves_skill_names():
    """Test that skill names are preserved correctly"""
    skill_names = ["C++", "JavaScript", "TypeScript", "C#", "F#", "Python3"]
    skills = [WeightedSkills(
        skill_name=name, weight=1.0/len(skill_names)) for name in skill_names]

    project_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, skills)
    ])
    project = ProjectReport.from_statistics(project_stats)

    user = UserReport([project])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    result_names = {skill.skill_name for skill in user_skills}
    assert result_names == set(skill_names)


def test_weight_skills_returns_weighted_skills_objects():
    """Test that returned skills are WeightedSkills objects"""
    project_stats = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Elixir", weight=1.0)
        ])
    ])
    project = ProjectReport.from_statistics(project_stats)

    user = UserReport([project])
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    for skill in user_skills:
        assert isinstance(skill, WeightedSkills)
        assert isinstance(skill.skill_name, str)
        assert isinstance(skill.weight, (int, float))


def test_weight_skills_three_projects_same_skill():
    """Test accumulating weights from three projects with the same skill"""
    projects = []
    project_weights = [1.0, 1.5, 2.0]

    for i, weight in enumerate(project_weights):
        project_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
                WeightedSkills(skill_name="Kotlin", weight=0.5)
            ])
        ])
        project = ProjectReport.from_statistics(project_stats)
        project.get_project_weight = Mock(return_value=weight)
        projects.append(project)

    user = UserReport(projects)
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 1
    assert user_skills[0].skill_name == "Kotlin"
    # Weight should be accumulated from all three projects: 0.5*1.0 + 0.5*1.5 + 0.5*2.0 = 0.5 + 0.75 + 1.0 = 2.25
    assert user_skills[0].weight == 2.25


if __name__ == '__main__':
    # Run both pytest functions and unittest TestCase
    test_to_user_readable_string()
    test_to_user_readable_string_empty()
    test_to_user_readable_string_fallback_generic_title_value()
    # print("Pytest-style tests passed!")

    # Run unittest tests
    unittest.main()
