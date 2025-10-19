"""
Tests for analyzer classes in src/classes/analyzer.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

import pytest

# Ensure local modules with non-package absolute imports (report, statistic)
# are importable during tests.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
CLASSES_DIR = SRC_DIR / "classes"
for p in (str(CLASSES_DIR), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.classes.analyzer import BaseFileAnalyzer, TextFileAnalyzer  # type: ignore  # noqa: E402
from src.classes.statistic import FileStatCollection  # type: ignore  # noqa: E402


@pytest.fixture
def temp_text_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.txt"
    # Write predictable content
    content = "Myles Jack wasn't down\n"
    p.write_text(content, encoding="utf-8")
    return p


def test_base_file_analyzer_analyze_returns_filereport_with_core_stats(temp_text_file: Path):
    analyzer = BaseFileAnalyzer(str(temp_text_file))
    report = analyzer.analyze()

    # Filepath is set
    assert getattr(report, "filepath", None) == str(temp_text_file)

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


def test_base_file_analyzer_nonexistent_file_logs_and_returns_empty(caplog):
    caplog.set_level("ERROR")
    bogus = str(CLASSES_DIR / "does_not_exist.xyz")
    analyzer = BaseFileAnalyzer(bogus)
    report = analyzer.analyze()

    # Should have logged an error
    assert any("Couldn't access metadata" in rec.message for rec in caplog.records)

    # Stats should be empty
    # Access internal statistics via to_dict for simplicity
    assert report.to_dict() == {}


def test_text_file_analyzer_analyze_raises_unimplemented(temp_text_file: Path):
    analyzer = TextFileAnalyzer(str(temp_text_file))
    with pytest.raises(ValueError, match="Unimplemented"):
        _ = analyzer.analyze()
