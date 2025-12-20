from src.classes.report import UserReport
from src.classes.statistic import (
    Statistic, UserStatCollection, WeightedSkills, ProjectStatCollection
)
from unittest.mock import Mock


def test_weight_skills_single_project_single_skill(project_report_from_stats):
    """Test weighting skills with a single project containing one skill"""
    # Create a project with one skill
    project_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
                  [WeightedSkills(skill_name="Python", weight=1.0)])
    ]
    project = project_report_from_stats(project_stats)

    # Mock the project weight
    project.get_project_weight = Mock(return_value=2.0)

    user = UserReport([project], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 1
    assert user_skills[0].skill_name == "Python"
    # Weight should be 1.0 * 2.0 = 2.0
    assert user_skills[0].weight == 2.0


def test_weight_skills_single_project_multiple_skills(project_report_from_stats):
    """Test weighting skills with a single project containing multiple skills"""
    # Create a project with multiple skills
    project_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Python", weight=0.5),
            WeightedSkills(skill_name="React", weight=0.3),
            WeightedSkills(skill_name="PostgreSQL", weight=0.2)
        ])
    ]
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 3
    skill_names = {skill.skill_name for skill in user_skills}
    assert skill_names == {"Python", "React", "PostgreSQL"}


def test_weight_skills_multiple_projects_overlapping_skills(project_report_from_stats):
    """Test that skill weights are accumulated across multiple projects"""
    # Project 1
    project1_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Python", weight=0.5),
            WeightedSkills(skill_name="React", weight=0.5)
        ])
    ]
    project1 = project_report_from_stats(project1_stats)
    project1.get_project_weight = Mock(return_value=1.5)

    # Project 2 with overlapping skill (Python)
    project2_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Python", weight=0.6),
            WeightedSkills(skill_name="Django", weight=0.4)
        ])
    ]
    project2 = project_report_from_stats(project2_stats)
    project2.get_project_weight = Mock(return_value=2.0)

    user = UserReport([project1, project2], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 3

    # Check Python skill has accumulated weight: 0.5*1.5 + 0.6*2.0 = 0.75 + 1.2 = 1.95
    python_skills = [s for s in user_skills if s.skill_name == "Python"]
    assert len(python_skills) == 1
    assert python_skills[0].weight == 1.95


def test_weight_skills_empty_project_list():
    """Test weighting skills with no projects"""
    user = UserReport([], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 0


def test_weight_skills_project_with_no_skills(project_report_from_stats):
    """Test weighting skills when project has no skills demonstrated"""
    # Project with no skills
    project_stats = []
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 0


def test_weight_skills_mixed_projects_some_with_skills(project_report_from_stats):
    """Test with some projects having skills and some having none"""
    # Project 1 with skills
    project1_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Java", weight=0.7)
        ])
    ]
    project1 = project_report_from_stats(project1_stats)

    # Project 2 without skills
    project2_stats = []
    project2 = project_report_from_stats(project2_stats)

    # Project 3 with skills
    project3_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Java", weight=0.6),
            WeightedSkills(skill_name="Spring", weight=0.4)
        ])
    ]
    project3 = project_report_from_stats(project3_stats)

    user = UserReport([project1, project2, project3], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 2
    skill_names = {skill.skill_name for skill in user_skills}
    assert skill_names == {"Java", "Spring"}


def test_weight_skills_incorporates_project_weight(project_report_from_stats):
    """Test that user skill weight incorporates project weight"""
    # Create projects with different weights

    # Project 1: Lower weight
    project1_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="TypeScript", weight=1.0)
        ])
    ]
    project1 = project_report_from_stats(project1_stats)
    project1.get_project_weight = Mock(return_value=1.0)

    # Project 2: Higher weight
    project2_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="TypeScript", weight=1.0)
        ])
    ]
    project2 = project_report_from_stats(project2_stats)
    project2.get_project_weight = Mock(return_value=2.5)

    user = UserReport([project1, project2], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    # Both projects contribute to TypeScript skill weight
    assert user_skills is not None
    assert len(user_skills) == 1
    assert user_skills[0].skill_name == "TypeScript"
    # Weight should be 1.0*1.0 + 1.0*2.5 = 3.5
    assert user_skills[0].weight == 3.5


def test_weight_skills_many_projects_many_skills(project_report_from_stats):
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
        project_stats = [
            Statistic(
                ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, skills)
        ]
        project = project_report_from_stats(project_stats)
        project.get_project_weight = Mock(return_value=weight)
        projects.append(project)

    user = UserReport(projects, "")
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


def test_weight_skills_creates_user_skills_statistic(project_report_from_stats):
    """Test that _weight_skills creates a USER_SKILLS statistic"""
    project_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Go", weight=1.0)
        ])
    ]
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "")

    # Check that USER_SKILLS statistic exists by retrieving the value
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)
    assert user_skills is not None
    assert isinstance(user_skills, list)


def test_weight_skills_identical_skills_same_project(project_report_from_stats):
    """Test handling of duplicate skill names within a project (edge case)"""
    # In practice this shouldn't happen, but let's test robustness
    project_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Rust", weight=0.6),
            WeightedSkills(skill_name="Rust", weight=0.4)  # Same skill twice
        ])
    ]
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    # Should handle gracefully - both should be accumulated
    assert user_skills is not None
    rust_skills = [s for s in user_skills if s.skill_name == "Rust"]
    # Either they accumulate into one or stay as separate entries
    assert len(rust_skills) >= 1


def test_weight_skills_preserves_skill_names(project_report_from_stats):
    """Test that skill names are preserved correctly"""
    skill_names = ["C++", "JavaScript", "TypeScript", "C#", "F#", "Python3"]
    skills = [WeightedSkills(
        skill_name=name, weight=1.0/len(skill_names)) for name in skill_names]

    project_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, skills)
    ]
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    result_names = {skill.skill_name for skill in user_skills}
    assert result_names == set(skill_names)


def test_weight_skills_returns_weighted_skills_objects(project_report_from_stats):
    """Test that returned skills are WeightedSkills objects"""
    project_stats = [
        Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
            WeightedSkills(skill_name="Elixir", weight=1.0)
        ])
    ]
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    for skill in user_skills:
        assert isinstance(skill, WeightedSkills)
        assert isinstance(skill.skill_name, str)
        assert isinstance(skill.weight, (int, float))


def test_weight_skills_three_projects_same_skill(project_report_from_stats):
    """Test accumulating weights from three projects with the same skill"""
    projects = []
    project_weights = [1.0, 1.5, 2.0]

    for i, weight in enumerate(project_weights):
        project_stats = [
            Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, [
                WeightedSkills(skill_name="Kotlin", weight=0.5)
            ])
        ]
        project = project_report_from_stats(project_stats)
        project.get_project_weight = Mock(return_value=weight)
        projects.append(project)

    user = UserReport(projects, "")
    user_skills = user.get_value(UserStatCollection.USER_SKILLS.value)

    assert user_skills is not None
    assert len(user_skills) == 1
    assert user_skills[0].skill_name == "Kotlin"
    # Weight should be accumulated from all three projects: 0.5*1.0 + 0.5*1.5 + 0.5*2.0 = 0.5 + 0.75 + 1.0 = 2.25
    assert user_skills[0].weight == 2.25
