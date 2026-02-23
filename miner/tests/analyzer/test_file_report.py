"""
Tests for the file report module. Any analyzer specific tests should be placed in
their respective test files.
"""

from src.core.statistic import (
    StatisticIndex, Statistic, FileStatCollection, FileDomain
)
from src.core.report import FileReport
import pytest


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
