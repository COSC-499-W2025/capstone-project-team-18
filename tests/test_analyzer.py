"""
Tests for analyzer classes in src/classes/analyzer.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime


import pytest

# Make sure that non-package imports (like `statistic`)
# can be imported
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
CLASSES_DIR = SRC_DIR / "classes"
# validate the all paths in the src/ and src/classes
# are stored in `sys.path` (a list of directories that Python
# uses to search for modules & packages)
for p in (str(CLASSES_DIR), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)  # add the path to sys.path if it's not there

from src.classes.analyzer import BaseFileAnalyzer, TextFileAnalyzer  # type: ignore  # noqa: E402
from src.classes.statistic import FileStatCollection  # type: ignore  # noqa: E402


@pytest.fixture
def temp_text_file(tmp_path: Path) -> Path:
    '''Create a temporary file that will be deleted after the test'''
    p = tmp_path / "sample.txt"
    content = "Myles Jack wasn't down\n"
    p.write_text(content, encoding="utf-8")
    return p


def test_base_file_analyzer_process_returns_file_report_with_core_stats(temp_text_file: Path):
    '''
    Test that the metadata of the file we created in `temp_text_file()` will be read and stored
    in a `FileReport` object by the `analyze()` function.
    '''
    analyzer = BaseFileAnalyzer(str(temp_text_file))
    report = analyzer.analyze()  # FileReport obj
    # Check that filepath is stored in report obj
    assert getattr(report, "filepath") == str(temp_text_file)

    # Core stats exist
    size = report.get_value(FileStatCollection.FILE_SIZE_BYTES.value)
    created = report.get_value(FileStatCollection.DATE_CREATED.value)
    accessed = report.get_value(FileStatCollection.DATE_ACCESSED.value)
    modified = report.get_value(FileStatCollection.DATE_MODIFIED.value)

    # Validate types and basic expectations
    assert isinstance(size, int) and size > 0
    assert isinstance(created, datetime)
    assert isinstance(accessed, datetime)
    assert isinstance(modified, datetime)

    # Size should match the actual file size
    assert size == temp_text_file.stat().st_size


def test_base_file_analyzer_nonexistent_file_logs_and_returns_empty():
    '''
    Test that the `analyze()` function returns nothing if an error is thrown
    '''
    fake_file = str(CLASSES_DIR / "does_not_exist.xyz")
    analyzer = BaseFileAnalyzer(fake_file)
    report = analyzer.analyze()

    # report's StatisticIndex should be empty
    assert len(report.statistics) == 0


def test_text_file_analyzer_analyze_raises_unimplemented(temp_text_file: Path):
    '''
    Currently, the `TextFileAnalyzer() function doesn't have any logic. Once it does,
    the test case(s) will be implemented here.
    '''
    analyzer = TextFileAnalyzer(str(temp_text_file))
    with pytest.raises(ValueError, match="Unimplemented"):
        _ = analyzer.analyze()


def test_extract_file_reports_recieves_empty_project():
    """
    Test that the extraction returns corrrect messaging upon reciept of an empty project directory
    """
