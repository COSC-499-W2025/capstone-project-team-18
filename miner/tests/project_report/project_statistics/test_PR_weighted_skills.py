from pytest import approx

from src.core.statistic import StatisticIndex, ProjectStatCollection, Statistic, FileStatCollection, ProjectStatCollection
from src.core.report import ProjectReport, FileReport
from src.core.report.project.project_statistics import ProjectWeightedSkills


def test_weighted_skills_from_imported_packages():
    """Ensure weighted skills are aggregated from imported packages across files."""

    # file1 imports numpy and pandas, file2 imports numpy
    file1_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                  ["numpy", "pandas"])
    ])
    file2_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["numpy"])
    ])

    file1 = FileReport(file1_stats, "file1.py")
    file2 = FileReport(file2_stats, "file2.py")

    project = ProjectReport([file1, file2], calculator_classes=[
                            ProjectWeightedSkills])

    skills = project.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    assert isinstance(skills, list)
    # build a name -> weight map for easier assertions
    weight_map = {ws.skill_name: ws.weight for ws in skills}

    # changed as numpy & panda both map to Data Analytics
    assert "Data Analytics" in weight_map
    assert weight_map["Data Analytics"] == 1


def test_multiple_weighted_skills_from_imported_packages():
    """Ensure weighted skills are aggregated from imported packages across files."""

    # file1 imports numpy and pandas, file2 imports numpy
    file1_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                  ["numpy", "pandas"])
    ])
    file2_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["numpy"])
    ])
    file3_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["sqlalchemy"])
    ])

    file1 = FileReport(file1_stats, "file1.py")
    file2 = FileReport(file2_stats, "file2.py")
    file3 = FileReport(file3_stats, "file3.py")
    project = ProjectReport([file1, file2, file3], calculator_classes=[
                            ProjectWeightedSkills])

    skills = project.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    assert isinstance(skills, list)
    # build a name -> weight map for easier assertions
    weight_map = {ws.skill_name: ws.weight for ws in skills}

    # assert both skills have been found
    assert "Data Analytics" in weight_map and "Database" in weight_map
    # data analytics found in two files, vs database in one file
    assert weight_map["Data Analytics"] == approx(
        2 / 3) and weight_map["Database"] == approx(1 / 3)

# true only if containing no filename matches


def test_weighted_skills_absent_when_no_imports():
    """If no files provide IMPORTED_PACKAGES, the project stat should not exist."""
    file_stats = StatisticIndex([])
    file_report = FileReport(file_stats, "no_imports.py")

    project = ProjectReport([file_report], calculator_classes=[
                            ProjectWeightedSkills])

    skills = project.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    assert skills is None


def test_filename_maps_to_skills():
    """If filename matches a user skill should be created"""

    file_stats = StatisticIndex([])
    file1 = FileReport(file_stats, "Dockerfile")
    file2 = FileReport(file_stats, "securityCheck.py")
    file3 = FileReport(file_stats, "database_migration.py")
    project = ProjectReport([file1, file2, file3], calculator_classes=[
                            ProjectWeightedSkills])

    skills = project.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    # build a name -> weight map for easier assertions
    weight_map = {ws.skill_name: ws.weight for ws in skills}
    assert "Containerization" in weight_map and "Security" in weight_map and "Database" in weight_map


def test_group_weighted_stats_include_non_user_authored_files(monkeypatch):
    file1_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["numpy"])
    ])
    file1 = FileReport(file1_stats, "file1.py")

    monkeypatch.setattr(
        ProjectWeightedSkills,
        "_get_nonUser_authors_per_file",
        lambda _self, _repo, _email, _github=None: {"file1.py": 1},
    )

    project = ProjectReport(
        [file1],
        project_path="Unknown Path",
        user_email="user@example.com",
        user_github="user",
        project_repo=object(),
        calculator_classes=[ProjectWeightedSkills],
    )

    group_skills = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_SKILLS_DEMONSTRATED.value)
    group_frameworks = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_FRAMEWORKS.value)

    assert isinstance(group_skills, list)
    assert isinstance(group_frameworks, list)
    assert any(ws.skill_name == "Data Analytics" for ws in group_skills)
    assert any(ws.skill_name == "numpy" for ws in group_frameworks)


def test_skill_activity_records_commit_dates_per_skill(project_shared_file):
    """
    PROJECT_SKILL_ACTIVITY should contain one date entry per commit that
    touched a file demonstrating that skill.

    Fixture: shared.py has 3 commits (alice, bob, charlie) and imports numpy
    → numpy maps to "Data Analytics" → activity list should have length 3.
    """
    import re as _re
    file_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["numpy"])
    ])
    shared_file = FileReport(file_stats, "shared.py")

    project = ProjectReport(
        [shared_file],
        project_path=str(project_shared_file.root_path),
        user_email="alice@example.com",
        project_repo=project_shared_file.repo,
        calculator_classes=[ProjectWeightedSkills],
    )

    calculator = ProjectWeightedSkills()
    skill_activity = calculator._build_project_skill_activity(
        project,
        project._get_sub_dirs(),
    )

    assert isinstance(skill_activity, dict)
    # numpy → "Data Analytics" skill
    assert "Data Analytics" in skill_activity
    # shared.py was committed 3 times, so 3 date entries
    dates = skill_activity["Data Analytics"]
    assert len(dates) == 3
    # every entry should be a YYYY-MM-DD string
    for d in dates:
        assert _re.match(r"\d{4}-\d{2}-\d{2}",
                         d), f"unexpected date format: {d}"


def test_group_weighted_stats_include_non_user_authored_files_git_based(project_shared_file):
    file_stats = StatisticIndex([
        Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["numpy"])
    ])
    shared_file = FileReport(file_stats, "shared.py")

    project = ProjectReport(
        [shared_file],
        project_path=str(project_shared_file.root_path),
        user_email="alice@example.com",
        user_github="user",
        project_repo=project_shared_file.repo,
        calculator_classes=[ProjectWeightedSkills],
    )

    group_skills = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_SKILLS_DEMONSTRATED.value)
    group_frameworks = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_FRAMEWORKS.value)

    assert isinstance(group_skills, list)
    assert isinstance(group_frameworks, list)
    assert any(ws.skill_name == "Data Analytics" for ws in group_skills)
    assert any(ws.skill_name == "numpy" for ws in group_frameworks)


def test_non_user_authors_excludes_user_noreply_email(tmp_path):
    """
    Files committed only via the user's GitHub noreply email must not appear
    in group skill stats — the noreply address should be treated as the user.
    """
    from git import Repo

    project_dir = tmp_path / "NoreplyProject"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    # Alice commits file1.py using her GitHub noreply email
    with repo.config_writer() as config:
        config.set_value("user", "name", "Alice")
        config.set_value("user", "email", "alice@users.noreply.github.com")
    (project_dir / "file1.py").write_text("import numpy")
    repo.index.add(["file1.py"])
    repo.index.commit("Alice via noreply")

    # Bob commits file2.py with a regular email
    with repo.config_writer() as config:
        config.set_value("user", "name", "Bob")
        config.set_value("user", "email", "bob@example.com")
    (project_dir / "file2.py").write_text("import sqlalchemy")
    repo.index.add(["file2.py"])
    repo.index.commit("Bob's commit")

    file1_stats = StatisticIndex(
        [Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["numpy"])])
    file2_stats = StatisticIndex(
        [Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["sqlalchemy"])])

    project = ProjectReport(
        [FileReport(file1_stats, "file1.py"),
         FileReport(file2_stats, "file2.py")],
        project_path=str(project_dir),
        user_email="alice@example.com",
        user_github="alice",
        project_repo=repo,
        calculator_classes=[ProjectWeightedSkills],
    )

    group_skills = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_SKILLS_DEMONSTRATED.value)
    group_frameworks = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_FRAMEWORKS.value)

    # Bob's sqlalchemy should appear in group stats
    assert isinstance(group_skills, list)
    assert any(ws.skill_name == "Database" for ws in group_skills)

    # Alice's noreply commit counts as the user, so Data Analytics must NOT be in group stats
    assert not any(ws.skill_name == "Data Analytics" for ws in group_skills)

    # numpy was only committed by alice's noreply address, so it must not appear as a group framework
    framework_names = [
        ws.skill_name for ws in group_frameworks] if group_frameworks else []
    assert "numpy" not in framework_names


def test_non_user_authors_includes_noreply_when_no_github_username(tmp_path):
    """
    Without a github username, a noreply email is treated as an unknown author
    and IS counted as a non-user contributor (backward-compatible behaviour).
    """
    from git import Repo

    project_dir = tmp_path / "NoreplyNoGithub"
    project_dir.mkdir()
    repo = Repo.init(project_dir)

    # Someone commits file1.py using a noreply-style email
    with repo.config_writer() as config:
        config.set_value("user", "name", "Stranger")
        config.set_value("user", "email", "stranger@users.noreply.github.com")
    (project_dir / "file1.py").write_text("import numpy")
    repo.index.add(["file1.py"])
    repo.index.commit("Stranger via noreply")

    file1_stats = StatisticIndex(
        [Statistic(FileStatCollection.IMPORTED_PACKAGES.value, ["numpy"])])

    # No user_github provided — noreply email is unrecognised, so it IS a non-user author
    project = ProjectReport(
        [FileReport(file1_stats, "file1.py")],
        project_path=str(project_dir),
        user_email="alice@example.com",
        user_github=None,
        project_repo=repo,
        calculator_classes=[ProjectWeightedSkills],
    )

    group_skills = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_SKILLS_DEMONSTRATED.value)

    # The noreply commit is treated as a different author, so Data Analytics IS in group stats
    assert isinstance(group_skills, list)
    assert any(ws.skill_name == "Data Analytics" for ws in group_skills)
