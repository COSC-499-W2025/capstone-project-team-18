from pathlib import Path
from src.classes.statistic import StatisticIndex, Statistic, FileStatCollection, ProjectStatCollection, CodingLanguage
from src.classes.analyzer import CodeFileAnalyzer, get_appropriate_analyzer
from src.classes.report import ProjectReport, FileReport
from datetime import datetime


def test_project_dates():
    # Create mock file reports with different dates
    file1_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 1, 1)),
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 1, 15))
    ])
    file1 = FileReport(file1_stats, "file1.py")

    file2_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 2, 1)),
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 2, 20))
    ])
    file2 = FileReport(file2_stats, "file2.py")

    # Create project report
    project = ProjectReport([file1, file2])

    # Test project start date (earliest created)
    start_date = project.get_value(
        ProjectStatCollection.PROJECT_START_DATE.value)
    assert start_date == datetime(2023, 1, 1)

    # Test project end date (latest modified)
    end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
    assert end_date == datetime(2023, 2, 20)


def test_empty_file_reports_list():
    """Test that empty file reports list doesn't crash"""
    project = ProjectReport([])

    # Should not have start or end dates
    start_date = project.get_value(
        ProjectStatCollection.PROJECT_START_DATE.value)
    end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)

    assert start_date is None
    assert end_date is None


def test_single_file_report():
    """Test with only one file report"""
    file_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value,
                  datetime(2023, 5, 10)),
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 5, 15))
    ])
    file_report = FileReport(file_stats, "single_file.py")

    project = ProjectReport([file_report])

    # Start and end should be the same file's dates
    start_date = project.get_value(
        ProjectStatCollection.PROJECT_START_DATE.value)
    end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)

    assert start_date == datetime(2023, 5, 10)
    assert end_date == datetime(2023, 5, 15)


def test_files_with_missing_dates():
    """Test files that have None values for dates"""
    # File with only creation date
    file1_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 3, 1))
    ])
    file1 = FileReport(file1_stats, "file1.py")

    # File with only modification date
    file2_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 3, 20))
    ])
    file2 = FileReport(file2_stats, "file2.py")

    # File with both dates
    file3_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 3, 5)),
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 3, 15))
    ])
    file3 = FileReport(file3_stats, "file3.py")

    project = ProjectReport([file1, file2, file3])

    # Should use earliest creation date from available files
    start_date = project.get_value(
        ProjectStatCollection.PROJECT_START_DATE.value)
    assert start_date == datetime(2023, 3, 1)

    # Should use latest modification date from available files
    end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
    assert end_date == datetime(2023, 3, 20)


def test_files_with_no_dates():
    """Test files that have no date statistics at all"""
    file_stats = StatisticIndex([])  # No statistics
    file_report = FileReport(file_stats, "no_dates.py")

    project = ProjectReport([file_report])

    # Should have no dates
    start_date = project.get_value(
        ProjectStatCollection.PROJECT_START_DATE.value)
    end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)

    assert start_date is None
    assert end_date is None


def test_wrong_date_assumptions():
    """Test that dates are calculated correctly with assertFalse"""
    file1_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 1, 1)),
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 1, 15))
    ])
    file1 = FileReport(file1_stats, "file1.py")

    file2_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 2, 1)),
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 2, 20))
    ])
    file2 = FileReport(file2_stats, "file2.py")

    project = ProjectReport([file1, file2])

    start_date = project.get_value(
        ProjectStatCollection.PROJECT_START_DATE.value)
    end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)

    # Assert wrong assumptions are false
    assert start_date != datetime(2023, 2, 1)  # Wrong start date
    assert end_date != datetime(2023, 1, 15)   # Wrong end date
    assert start_date != end_date             # Start != End
    # Start should be before end
    assert start_date <= end_date


def test_multiple_files_complex_dates():
    """Test with many files and complex date patterns"""
    files = []

    # Create 5 files with various dates
    dates = [
        (datetime(2023, 1, 5), datetime(2023, 1, 10)),   # Earliest creation
        (datetime(2023, 3, 1), datetime(2023, 3, 25)),
        (datetime(2023, 2, 15), datetime(2023, 4, 30)),  # Latest modification
        (datetime(2023, 1, 20), datetime(2023, 2, 5)),
        (datetime(2023, 2, 1), datetime(2023, 3, 15))
    ]

    for i, (created, modified) in enumerate(dates):
        stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, created),
            Statistic(FileStatCollection.DATE_MODIFIED.value, modified)
        ])
        files.append(FileReport(stats, f"file{i}.py"))

    project = ProjectReport(files)

    start_date = project.get_value(
        ProjectStatCollection.PROJECT_START_DATE.value)
    end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)

    # Should be earliest creation and latest modification
    assert start_date == datetime(2023, 1, 5)
    assert end_date == datetime(2023, 4, 30)

    # Assert false conditions
    assert start_date != datetime(
        2023, 1, 20)  # Not the second earliest
    assert end_date != datetime(2023, 3, 25)  # Not the second latest


def test_project_report_inheritance():
    """Test that ProjectReport properly inherits from BaseReport"""
    file_stats = StatisticIndex([
        Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 1, 1)),
        Statistic(FileStatCollection.DATE_MODIFIED.value,
                  datetime(2023, 1, 15))
    ])
    file_report = FileReport(file_stats, "test.py")

    project = ProjectReport([file_report])

    # Test inherited methods work
    assert project.to_dict() is not None
    assert isinstance(project.to_dict(), dict)

    # Test that repr doesn't crash
    repr_str = repr(project)
    assert isinstance(repr_str, str)
    assert "ProjectReport" in repr_str


def test_coding_ratio_in_normal_project(tmp_path):
    """
    Tests that we have approiate coding ratio
    of files
    """

    files = ["file.c",
             "file2.c",
             "file3.py",
             "file4.rb",
             "file5.py",
             "file6.docx",
             "file7.md"]

    expected_ratio = {
        CodingLanguage.C: (2/5),
        CodingLanguage.PYTHON: (2/5),
        CodingLanguage.RUBY: (1/5)
    }

    # We should see C language be 0.4, py be 0.4 and ruby be 0.2

    reports = []

    # Make files and log their reports
    for file in files:
        path = tmp_path / file
        Path(path).write_text("")

        reports.append(get_appropriate_analyzer(path).analyze())

    project_report = ProjectReport(reports)

    coding_language_ratio = project_report.get_value(
        ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

    assert len(coding_language_ratio) == len(expected_ratio)
    assert isinstance(coding_language_ratio, dict)

    for language in expected_ratio.keys():
        ratio = coding_language_ratio.get(language, None)

        assert ratio == expected_ratio.get(language)


def test_weighted_skills_from_imported_packages():
    """Ensure weighted skills are aggregated from imported packages across files."""
    from pytest import approx
    from src.classes.statistic import Statistic, StatisticIndex, FileStatCollection, ProjectStatCollection

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

    assert "numpy" in weight_map and "pandas" in weight_map
    assert weight_map["numpy"] == approx(2 / 3)
    assert weight_map["pandas"] == approx(1 / 3)


def test_weighted_skills_absent_when_no_imports():
    """If no files provide IMPORTED_PACKAGES, the project stat should not exist."""
    file_stats = StatisticIndex([])
    file_report = FileReport(file_stats, "no_imports.py")

    project = ProjectReport([file_report])

    skills = project.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    assert skills is None
