"""
Tests for BaseFileAnalyzer and extract_file_reports.
"""

from pathlib import Path
from datetime import datetime
import pytest
from src.core.analyzer import (
    BaseFileAnalyzer,
    extract_file_reports,
    get_appropriate_analyzer,
)
from src.core.statistic import FileStatCollection
from src.core.project_discovery.project_discovery import ProjectLayout
from src.utils.pathing_utils import unzip_file
from src.database.api.models import UserConfigModel


def test_base_file_analyzer_process_returns_file_report_with_core_stats(
    temp_text_file: list[str], project_context_from_root
):
    analyzer = BaseFileAnalyzer(
        UserConfigModel(),
        project_context_from_root(temp_text_file[0]),
        temp_text_file[1],
    )
    report = analyzer.analyze()
    assert getattr(report, "filepath") == temp_text_file[1]

    size = report.get_value(FileStatCollection.FILE_SIZE_BYTES.value)
    created = report.get_value(FileStatCollection.DATE_CREATED.value)
    modified = report.get_value(FileStatCollection.DATE_MODIFIED.value)

    assert isinstance(size, int) and size > 0
    assert isinstance(created, datetime)
    assert isinstance(modified, datetime)
    assert size == Path(
        temp_text_file[0] + "/" + temp_text_file[1]).stat().st_size


def test_base_file_analyzer_nonexistent_file_logs_and_returns_empty(
    project_context_from_root,
):
    fake_file = "does_not_exist.xyz"
    analyzer = BaseFileAnalyzer(
        UserConfigModel(), project_context_from_root(""), fake_file
    )

    with pytest.raises(Exception):
        analyzer.analyze()


def test_extract_file_reports_returns_project(tmp_path, create_temp_file):
    files = ["t1est1.txt", "test2.txt", "test3.txt", "test4.txt", "test5.txt"]

    for filename in files:
        create_temp_file(filename, "Sample content", tmp_path)

    project_file = ProjectLayout(
        name="TestProject",
        root_path=tmp_path,
        file_paths=[Path(f) for f in files],
        repo=None,
    )

    listReport = extract_file_reports(
        user_config=UserConfigModel(), project_file=project_file
    )
    assert listReport is not None
    assert len(listReport) == 5 and all(
        isinstance(report, object) for report in listReport
    )


def test_created_modifiyed_and_accessed_dates(tmp_path, project_context_from_root):
    unzip_file("tests/resources/mac_projects.zip", str(tmp_path))

    file_path = tmp_path / "Projects" / "ProjectA" / "a_1.txt"

    report = BaseFileAnalyzer(
        UserConfigModel(),
        project_context_from_root(str(file_path.parent)),
        file_path.name,
    ).analyze()

    date_modified = report.get_value(FileStatCollection.DATE_MODIFIED.value)
    date_created = report.get_value(FileStatCollection.DATE_CREATED.value)

    assert date_modified == datetime(2025, 10, 20, 21, 38, 6)
    assert date_created == datetime(2025, 10, 20, 21, 38, 6)
    assert date_created <= date_modified


def test_extract_file_reports_recieves_project_with_subfolder(
    tmp_path, create_temp_file
):
    create_temp_file("a_1.txt", "File One", tmp_path)
    create_temp_file("a_2.txt", "File Two", tmp_path)
    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()
    create_temp_file("a_3.txt", "File Three", subfolder)

    project_file = ProjectLayout(
        name="ProjectA",
        root_path=tmp_path,
        file_paths=[Path("a_1.txt"), Path("a_2.txt"),
                    Path("subfolder/a_3.txt")],
        repo=None,
    )

    listReport = extract_file_reports(
        user_config=UserConfigModel(), project_file=project_file
    )

    assert listReport is not None
    assert len(listReport) == 3 and all(
        isinstance(report, object) for report in listReport
    )


def test_create_with_analysis_unknown_file_type(
    tmp_path, create_temp_file, project_context_from_root
):
    """Test analysis for unknown file types falls back to base analyzer."""
    content = "Some content"

    file_path = create_temp_file("test.unknown", content, tmp_path)
    analyzer = get_appropriate_analyzer(
        UserConfigModel(), project_context_from_root(str(tmp_path)), "test.unknown"
    )
    file_report = analyzer.analyze()

    # Should have basic file statistics
    assert file_report.get_value(
        FileStatCollection.FILE_SIZE_BYTES.value) is not None
    assert file_report.get_value(
        FileStatCollection.DATE_CREATED.value) is not None

    # Should not have specialized statistics
    assert file_report.get_value(FileStatCollection.WORD_COUNT.value) is None
    assert file_report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value) is None


def test_create_with_analysis_empty_file(
    tmp_path, create_temp_file, project_context_from_root
):
    """Test analysis of empty files."""
    file_path = create_temp_file("empty.py", "", tmp_path)
    analyzer = get_appropriate_analyzer(
        UserConfigModel(), project_context_from_root(str(tmp_path)), "empty.py"
    )
    file_report = analyzer.analyze()

    # Should have basic file statistics
    assert file_report.get_value(
        FileStatCollection.FILE_SIZE_BYTES.value) is not None
    size = file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value)
    assert size == 0
