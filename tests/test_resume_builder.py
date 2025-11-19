from src.classes.resume import coding_language_bp, weight_skills_bp, bullet_point_builder
from src.classes.statistic import (
    WeightedSkills,
    CodingLanguage,
    Statistic,
    StatisticIndex,
    ProjectStatCollection,
)
from src.classes.report import ProjectReport


def test_coding_language_bp_multiple():
    ratio = {CodingLanguage.PYTHON: 0.6, CodingLanguage.JAVASCRIPT: 0.4}
    bp = coding_language_bp(ratio)
    assert "Python" in bp
    assert "Javascript" in bp
    assert bp.startswith("Implemented code mainly in")


def test_coding_language_bp_single():
    ratio = {CodingLanguage.PYTHON: 1.0}
    bp = coding_language_bp(ratio)
    assert bp == "Project was coded using the Python language"


def test_coding_language_bp_small_shares():
    ratio = {CodingLanguage.PYTHON: 0.05, CodingLanguage.JAVASCRIPT: 0.05}
    bp = coding_language_bp(ratio)
    assert "small amounts" in bp


def test_weight_skills_bp_top_three():
    skills = [
        WeightedSkills("Machine Learning", 0.9),
        WeightedSkills("Python", 0.8),
        WeightedSkills("Docker", 0.3),
        WeightedSkills("CI/CD", 0.2),
    ]
    bp = weight_skills_bp(skills)
    assert "Machine Learning" in bp
    assert "Python" in bp
    assert "Docker" in bp
    # only top three should be present
    assert "CI/CD" not in bp


def test_bullet_point_builder_aggregates_stats():
    stats = [
        Statistic(
            ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
            {CodingLanguage.PYTHON: 0.6, CodingLanguage.JAVASCRIPT: 0.4},
        ),
        Statistic(
            ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
            [WeightedSkills("ML", 0.9), WeightedSkills("Python", 0.8)],
        ),
        Statistic(ProjectStatCollection.IS_GROUP_PROJECT.value, True),
        Statistic(ProjectStatCollection.TOTAL_AUTHORS.value, 3),
        Statistic(ProjectStatCollection.AUTHORS_PER_FILE.value,
                  {"a.py": 1, "b.js": 2}),
        Statistic(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value, 25.0),
        Statistic(ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value, 40.0),
    ]

    si = StatisticIndex(stats)
    report = ProjectReport.from_statistics(si)

    bullets = bullet_point_builder(report)

    # should include language, skills, collaboration, and percentages
    assert any("python" in b.lower() for b in bullets)
    assert any("ml" in b.lower() or "machine" in b.lower() for b in bullets)
    assert any("collaborated" in b.lower() for b in bullets)
    assert any("authored 25.0%" in b.lower()
               or "authored 25%" in b.lower() for b in bullets)
    assert any("accounted for 40.0%" in b.lower()
               or "accounted for 40%" in b.lower() for b in bullets)


def test_bullet_point_builder_individual():
    stats = [
        Statistic(ProjectStatCollection.IS_GROUP_PROJECT.value, False),
    ]
    si = StatisticIndex(stats)
    report = ProjectReport.from_statistics(si)
    bullets = bullet_point_builder(report)
    assert any("individ" in b.lower() for b in bullets)
