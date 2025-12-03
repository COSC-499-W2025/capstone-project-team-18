"""
Tests for language filtering functionality
"""
import pytest
from pathlib import Path
from src.classes.analyzer import get_appropriate_analyzer, extract_file_reports
from src.utils.project_discovery.project_discovery import ProjectFiles
from src.classes.statistic import CodingLanguage
from git import Repo


def test_language_filter_excludes_non_matching_files(tmp_path):
    """Test that files not matching the language filter are excluded"""
    # Create test files
    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')")

    js_file = tmp_path / "test.js"
    js_file.write_text("console.log('hello')")

    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")

    # Create ProjectFiles with RELATIVE paths from root_path
    project = ProjectFiles(
        name="test_project",
        root_path=str(tmp_path),
        file_paths=["test.py", "test.js", "test.html"],
        repo=None
    )

    # Test with Python-only filter
    language_filter = ["Python"]
    file_reports = extract_file_reports(project, None, language_filter)

    # Should only include Python file
    assert file_reports is not None
    assert len(file_reports) == 1
    assert "test.py" in file_reports[0].filepath


def test_language_filter_includes_matching_files(tmp_path):
    """Test that files matching the language filter are included"""
    # Create test files
    py_file = tmp_path / "script.py"
    py_file.write_text("def hello(): pass")

    js_file = tmp_path / "app.js"
    js_file.write_text("function hello() {}")

    css_file = tmp_path / "style.css"
    css_file.write_text("body { color: red; }")

    # Create ProjectFiles with RELATIVE paths
    project = ProjectFiles(
        name="test_project",
        root_path=str(tmp_path),
        file_paths=["script.py", "app.js", "style.css"],
        repo=None
    )

    # Test with multiple languages
    language_filter = ["Python", "Javascript", "Css"]
    file_reports = extract_file_reports(project, None, language_filter)

    # Should include all three files
    assert file_reports is not None
    assert len(file_reports) == 3
    file_paths = [fr.filepath for fr in file_reports]
    assert any("script.py" in fp for fp in file_paths)
    assert any("app.js" in fp for fp in file_paths)
    assert any("style.css" in fp for fp in file_paths)


def test_language_filter_empty_allows_all(tmp_path):
    """Test that empty language filter allows all files"""
    # Create test files
    py_file = tmp_path / "test.py"
    py_file.write_text("print('test')")

    js_file = tmp_path / "test.js"
    js_file.write_text("console.log('test')")

    # Create ProjectFiles with RELATIVE paths
    project = ProjectFiles(
        name="test_project",
        root_path=str(tmp_path),
        file_paths=["test.py", "test.js"],
        repo=None
    )

    # Test with empty filter (should include all)
    language_filter = []
    file_reports = extract_file_reports(project, None, language_filter)

    # Should include both files
    assert file_reports is not None
    assert len(file_reports) == 2


def test_language_filter_case_insensitive(tmp_path):
    """Test that language filter is case-insensitive"""
    # Create test file
    py_file = tmp_path / "test.py"
    py_file.write_text("print('test')")

    # Create ProjectFiles with RELATIVE path
    project = ProjectFiles(
        name="test_project",
        root_path=str(tmp_path),
        file_paths=["test.py"],
        repo=None
    )

    # Test with different casings
    for filter_variant in [["python"], ["PYTHON"], ["Python"], ["pYtHoN"]]:
        file_reports = extract_file_reports(project, None, filter_variant)
        assert file_reports is not None
        assert len(file_reports) == 1


def test_should_include_respects_language_filter(tmp_path):
    """Test that BaseFileAnalyzer.should_include() respects language filter"""
    # Create Python file
    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')")

    # Test with Python in filter - should include
    analyzer = get_appropriate_analyzer(
        str(tmp_path),
        "test.py",
        None,
        None,
        ["Python"]
    )
    assert analyzer.should_inculde() is True

    # Test with only JavaScript in filter - should exclude
    analyzer = get_appropriate_analyzer(
        str(tmp_path),
        "test.py",
        None,
        None,
        ["Javascript"]
    )
    assert analyzer.should_inculde() is False


def test_language_filter_with_multiple_extensions(tmp_path):
    """Test language filter works with files that have multiple possible extensions"""
    # Create TypeScript files
    ts_file = tmp_path / "app.ts"
    ts_file.write_text("const x: number = 5;")

    tsx_file = tmp_path / "component.tsx"
    tsx_file.write_text("const Component = () => <div>Hello</div>;")

    # Create ProjectFiles with RELATIVE paths
    project = ProjectFiles(
        name="test_project",
        root_path=str(tmp_path),
        file_paths=["app.ts", "component.tsx"],
        repo=None
    )

    # Test with TypeScript filter
    language_filter = ["Typescript"]
    file_reports = extract_file_reports(project, None, language_filter)

    # Should include both .ts and .tsx files
    assert file_reports is not None
    assert len(file_reports) == 2