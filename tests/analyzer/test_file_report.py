"""
Tests for the file report module. Any analyzer specific tests should be placed in
their respective test files.
"""

from src.classes.statistic import (
    StatisticIndex, Statistic, FileStatCollection, FileDomain
)
from src.classes.report import FileReport
from src.classes.analyzer import get_appropriate_analyzer
import pytest
from tests.conftest import _create_temp_file


@pytest.mark.parametrize("filepath,expected_filename", [
    ("/path/to/file.py", "file.py"),
    ("./relative/path/document.md", "document.md"),
    ("simple.txt", "simple.txt"),
    ("/complex/path/with.multiple.dots.js", "with.multiple.dots.js")
])
def test_get_filename(filepath, expected_filename):
    """Test filename extraction from filepath."""
    stats = StatisticIndex()
    file_report = FileReport(stats, filepath)
    assert file_report.get_filename() == expected_filename


def test_file_report_basic_construction():
    """Test basic FileReport construction with statistics."""
    stats = StatisticIndex([
        Statistic(FileStatCollection.LINES_IN_FILE.value, 25),
        Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 1024)
    ])

    file_report = FileReport(stats, "example.txt")

    assert file_report.filepath == "example.txt"
    assert file_report.get_value(
        FileStatCollection.LINES_IN_FILE.value) == 25
    assert file_report.get_value(
        FileStatCollection.FILE_SIZE_BYTES.value) == 1024


def test_multiple_file_analysis_consistency(tmp_path):
    """Test that analyzing the same file multiple times gives consistent results."""
    content = (
        "def test_function():\n"
        "    '''Test function'''\n"
        "    return 42\n\n"
        "class TestClass:\n"
        "    def method(self):\n"
        "        pass\n"
    )

    file_path = _create_temp_file("consistency.py", content, tmp_path)

    # Analyze the same file multiple times
    analyzer1 = get_appropriate_analyzer(file_path[0], file_path[1])
    analyzer2 = get_appropriate_analyzer(file_path[0], file_path[1])

    report1 = analyzer1.analyze()
    report2 = analyzer2.analyze()

    # Results should be consistent
    for stat in FileStatCollection:
        assert (report1.get_value(stat.value) == report2.get_value(stat.value))


def test_file_report_statistics_integration():
    """Test integration between FileReport and StatisticIndex."""
    stats = StatisticIndex([
        Statistic(FileStatCollection.LINES_IN_FILE.value, 100),
        Statistic(FileStatCollection.WORD_COUNT.value, 500),
        Statistic(FileStatCollection.TYPE_OF_FILE.value,
                  FileDomain.DOCUMENTATION)
    ])

    file_report = FileReport(stats, "test.md")

    # Test all statistics are accessible
    assert file_report.get_value(FileStatCollection.LINES_IN_FILE.value) == 100
    assert file_report.get_value(FileStatCollection.WORD_COUNT.value) == 500
    assert file_report.get_value(
        FileStatCollection.TYPE_OF_FILE.value) == FileDomain.DOCUMENTATION

    # Test to_dict works
    result_dict = file_report.to_dict()
    assert "LINES_IN_FILE" in result_dict
    assert "WORD_COUNT" in result_dict
    assert "TYPE_OF_FILE" in result_dict


def test_file_report_add_statistic():
    """Test adding statistics to FileReport after creation."""
    stats = StatisticIndex()
    file_report = FileReport(stats, "test.py")

    # Add a statistic
    new_stat = Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 2048)
    file_report.add_statistic(new_stat)

    # Verify it was added
    assert file_report.get_value(
        FileStatCollection.FILE_SIZE_BYTES.value) == 2048
