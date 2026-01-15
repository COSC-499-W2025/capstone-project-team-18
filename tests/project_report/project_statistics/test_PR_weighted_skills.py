from src.core.statistic import StatisticIndex, ProjectStatCollection
from src.core.report import ProjectReport, FileReport


def test_weighted_skills_from_imported_packages():
    """Ensure weighted skills are aggregated from imported packages across files."""
    from pytest import approx
    from src.core.statistic import Statistic, StatisticIndex, FileStatCollection, ProjectStatCollection

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

    project = ProjectReport([file1, file2])

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
    from pytest import approx
    from src.core.statistic import Statistic, StatisticIndex, FileStatCollection, ProjectStatCollection

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
    project = ProjectReport([file1, file2, file3])

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

    project = ProjectReport([file_report])

    skills = project.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    assert skills is None


def test_filename_maps_to_skills():
    """If filename matches a user skill should be created"""

    file_stats = StatisticIndex([])
    file1 = FileReport(file_stats, "Dockerfile")
    file2 = FileReport(file_stats, "securityCheck.py")
    file3 = FileReport(file_stats, "database_migration.py")
    project = ProjectReport([file1, file2, file3])

    skills = project.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    # build a name -> weight map for easier assertions
    weight_map = {ws.skill_name: ws.weight for ws in skills}
    assert "Containerization" in weight_map and "Security" in weight_map and "Database" in weight_map
