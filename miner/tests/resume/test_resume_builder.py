from src.core.resume.bullet_point_builder import (
    BulletPointBuilder,
    ActivityTypeContributionBulletPoint,
    CodingLanguageBulletPoint,
    WeightedSkillsBulletPoint,
    ContributionPatternBulletPoint,
    ProjectThemesBulletPoint,
)
from src.core.statistic import (
    WeightedSkills,
    CodingLanguage,
    Statistic,
    ProjectStatCollection,
    FileDomain
)


def test_activity_type_contribution_bp_expected():
    """
    Check expected behavior of ActivityTypeContributionRule
    """

    ratio = {
        FileDomain.CODE: 0.12,
        FileDomain.DESIGN: 0.28,
        FileDomain.DOCUMENTATION: 0.30,
        FileDomain.TEST: 0.30
    }

    report = type("Report", (), {"get_value": lambda self, key: ratio})()
    bp = ActivityTypeContributionBulletPoint().generate(report)[
        0]  # type: ignore

    assert f"12% on code, 28% on design, 30% on documentation, 30% on test" in bp


def test_activity_type_contribution_bp_one_leading():
    """
    Check where on file domain dominates ActivityTypeContributionRule
    """

    ratio = {
        FileDomain.CODE: 0.9999991,
        FileDomain.DESIGN: 0.0000009
    }

    report = type("Report", (), {"get_value": lambda self, key: ratio})()
    bp = ActivityTypeContributionBulletPoint().generate(report)  # type: ignore

    assert len(bp) == 0


def test_activity_type_contribution_bp_near_zero():
    """
    Check behavior near zero of ActivityTypeContributionRule
    """

    ratio = {
        FileDomain.CODE: 0.3999999,
        FileDomain.TEST: 0.6,
        FileDomain.DESIGN: 0.0000001
    }

    report = type("Report", (), {"get_value": lambda self, key: ratio})()
    bp = ActivityTypeContributionBulletPoint().generate(report)[
        0]  # type: ignore

    assert f"40% on code, 60% on test" in bp
    assert "design" not in bp


def test_coding_language_bp_multiple():
    ratio = {CodingLanguage.PYTHON: 0.6, CodingLanguage.JAVASCRIPT: 0.4}
    report = type("Report", (), {"get_value": lambda self, key: ratio})()
    bp = CodingLanguageBulletPoint().generate(report)[0]  # type: ignore

    assert "Python" in bp
    assert "Javascript" in bp or "JavaScript" in bp
    assert bp.startswith("Implemented code mainly in")


def test_coding_language_bp_single():
    ratio = {CodingLanguage.PYTHON: 1.0}
    report = type("Report", (), {"get_value": lambda self, key: ratio})()
    bp = CodingLanguageBulletPoint().generate(report)[0]  # type: ignore
    assert bp == "Built the project utilizing Python"


def test_coding_language_bp_small_shares():
    ratio = {CodingLanguage.PYTHON: 0.05, CodingLanguage.JAVASCRIPT: 0.05}
    report = type("Report", (), {"get_value": lambda self, key: ratio})()
    bp = CodingLanguageBulletPoint().generate(report)[0]  # type: ignore

    assert "small amounts" in bp


def test_weight_skills_bp_top_three():
    skills = [
        WeightedSkills("Machine Learning", 0.9),
        WeightedSkills("Python", 0.8),
        WeightedSkills("Docker", 0.3),
        WeightedSkills("CI/CD", 0.2),
    ]
    report = type("Report", (), {"get_value": lambda self, key: skills})()
    bp = WeightedSkillsBulletPoint().generate(report)[0]  # type: ignore

    assert "Machine Learning" in bp
    assert "Python" in bp
    assert "Docker" in bp
    # only top three should be present
    assert "CI/CD" not in bp


def test_bullet_point_builder_aggregates_stats(project_report_from_stats):
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

    report = project_report_from_stats(stats)

    bp = BulletPointBuilder()
    bullets = bp.build(report)

    # should include language, skills, and collaboration bullets
    assert any("python" in b.lower() for b in bullets)
    assert any("ml" in b.lower() or "machine" in b.lower() for b in bullets)
    assert any("collaborated" in b.lower() for b in bullets)
    # contrib % (40.0) is higher than commit % (25.0) → only "delivered" bullet
    assert any("delivered 40.0%" in b.lower() or "delivered 40%" in b.lower() for b in bullets)
    assert not any("drove 25" in b.lower() for b in bullets)


def test_bullet_point_builder_individual(project_report_from_stats):
    stats = [
        Statistic(ProjectStatCollection.IS_GROUP_PROJECT.value, False),
    ]
    report = project_report_from_stats(stats)
    bp = BulletPointBuilder()
    bullets = bp.build(report)
    assert any("independ" in b.lower() for b in bullets)


def test_contribution_pattern_bp_role_mapped(monkeypatch):
    """COLLABORATION_ROLE is mapped to a resume-quality phrase."""
    import src.core.resume.bullet_point_builder as bpb
    monkeypatch.setattr(bpb, "ml_extraction_allowed", lambda: True)

    def get_value(self, key):
        if key == ProjectStatCollection.COLLABORATION_ROLE.value:
            return "leader"
        return None

    report = type("Report", (), {"get_value": get_value})()
    bullets = ContributionPatternBulletPoint().generate(report)  # type: ignore
    assert any("led" in b.lower() for b in bullets)
    assert not any(b == "leader" for b in bullets)


def test_contribution_pattern_bp_occasional_role_skipped(monkeypatch):
    """Occasional and solo roles produce no role bullet."""
    import src.core.resume.bullet_point_builder as bpb
    monkeypatch.setattr(bpb, "ml_extraction_allowed", lambda: True)

    for role in ["occasional", "solo"]:
        def get_value(self, key, _role=role):
            if key == ProjectStatCollection.COLLABORATION_ROLE.value:
                return _role
            return None

        report = type("Report", (), {"get_value": get_value})()
        bullets = ContributionPatternBulletPoint().generate(report)  # type: ignore
        assert not any(role in b for b in bullets)


def test_contribution_pattern_bp_commit_dist_mapped(monkeypatch):
    """Commit type labels are mapped to action-verb phrases."""
    import src.core.resume.bullet_point_builder as bpb
    monkeypatch.setattr(bpb, "ml_extraction_allowed", lambda: True)

    dist = {"feat": 40.0, "fix": 35.0, "unknown": 25.0}

    def get_value(self, key):
        if key == ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value:
            return dist
        return None

    report = type("Report", (), {"get_value": get_value})()
    bullets = ContributionPatternBulletPoint().generate(report)  # type: ignore
    assert any("spearheaded feature development" in b.lower() for b in bullets)
    assert any("40%" in b for b in bullets)
    assert not any(b.lower().startswith("primary contribution focus") for b in bullets)
    # "unknown" should be filtered out
    assert not any("unknown" in b.lower() for b in bullets)


def test_project_themes_bp_multiple(monkeypatch):
    """Multiple themes produce a spanning sentence."""
    import src.core.resume.bullet_point_builder as bpb
    monkeypatch.setattr(bpb, "ml_extraction_allowed", lambda: True)

    themes = ["Microsoft Azure AI integration", "Pronunciation feedback and phonics training", "React and Next.js"]

    report = type("Report", (), {"get_value": lambda self, key: themes})()
    bullets = ProjectThemesBulletPoint().generate(report)  # type: ignore
    assert len(bullets) == 1
    assert "Microsoft Azure AI integration" in bullets[0]
    assert bullets[0].startswith("Developed solutions spanning")
    # should cap at 2 themes
    assert "React and Next.js" not in bullets[0]


def test_project_themes_bp_ml_disabled(monkeypatch):
    """No themes bullet when ML is disabled."""
    import src.core.resume.bullet_point_builder as bpb
    monkeypatch.setattr(bpb, "ml_extraction_allowed", lambda: False)

    report = type("Report", (), {"get_value": lambda self, key: ["theme1"]})()
    bullets = ProjectThemesBulletPoint().generate(report)  # type: ignore
    assert len(bullets) == 0
