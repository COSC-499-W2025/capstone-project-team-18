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
        lambda _self, _repo, _email: {"file1.py": 1},
    )

    project = ProjectReport(
        [file1],
        project_path="Unknown Path",
        user_email="user@example.com",
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


def test_group_weighted_stats_include_non_user_authored_files_git_based(project_shared_file):
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

    group_skills = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_SKILLS_DEMONSTRATED.value)
    group_frameworks = project.get_value(
        ProjectStatCollection.GROUP_PROJECT_FRAMEWORKS.value)

    assert isinstance(group_skills, list)
    assert isinstance(group_frameworks, list)
    assert any(ws.skill_name == "Data Analytics" for ws in group_skills)
    assert any(ws.skill_name == "numpy" for ws in group_frameworks)
