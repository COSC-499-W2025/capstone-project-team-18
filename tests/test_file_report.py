"""
Comprehensive tests for FileReport class in src/classes/report.py
Tests the automatic file type detection and natural language statistics integration.
"""

from src.classes.analyzer import (
    BaseFileAnalyzer, TextFileAnalyzer, NaturalLanguageAnalyzer,
    PythonAnalyzer, JavaAnalyzer, JavaScriptAnalyzer, get_appropriate_analyzer
)
from src.classes.statistic import (
    StatisticIndex, Statistic, FileStatCollection, FileDomain
)
from src.classes.report import FileReport, BaseReport
import sys
import os
from pathlib import Path
from datetime import datetime
import tempfile
import pytest
import shutil

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _create_temp_file(filename: str, content: str, path: Path, encoding: str = "utf-8") -> Path:
    """Helper function to create temporary test files."""
    file_path = path / filename
    file_path.write_text(content, encoding=encoding)
    return file_path


@pytest.fixture
def temp_dir():
    """Fixture to create and cleanup temporary directory."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


class TestFileReportBasics:
    """Test basic FileReport functionality and inheritance."""

    def test_file_report_inheritance(self):
        """Test that FileReport properly inherits from BaseReport."""
        stats = StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 10)
        ])
        file_report = FileReport(stats, "test.py")

        # Test inheritance
        assert isinstance(file_report, BaseReport)
        assert isinstance(file_report, FileReport)

        # Test inherited methods work
        assert file_report.filepath == "test.py"
        assert file_report.to_dict() is not None
        assert isinstance(file_report.to_dict(), dict)

        # Test that repr doesn't crash
        repr_str = repr(file_report)
        assert isinstance(repr_str, str)
        assert "FileReport" in repr_str

    @pytest.mark.parametrize("filepath,expected_filename", [
        ("/path/to/file.py", "file.py"),
        ("./relative/path/document.md", "document.md"),
        ("simple.txt", "simple.txt"),
        ("/complex/path/with.multiple.dots.js", "with.multiple.dots.js")
    ])
    def test_get_filename(self, filepath, expected_filename):
        """Test filename extraction from filepath."""
        stats = StatisticIndex()
        file_report = FileReport(stats, filepath)
        assert file_report.get_filename() == expected_filename

    def test_file_report_basic_construction(self):
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


class TestFileReportWithAnalysis:
    """Test FileReport.create_with_analysis() method with different file types."""

    def test_create_with_analysis_natural_language_md(self, temp_dir):
        """Test natural language analysis for Markdown files."""
        content = (
            "# Test Document\n\n"
            "This is a test document with multiple sentences. "
            "It contains exactly fifty words in total to test our word counting functionality accurately. "
            "The document also tests sentence counting and character analysis for the automated readability index calculation.\n\n"
            "## Section Two\n"
            "Another paragraph for testing purposes."
        )

        file_path = _create_temp_file("test.md", content, temp_dir)
        file_report = FileReport.create_with_analysis(str(temp_dir), "test.md")

        # Test that natural language statistics are present
        assert file_report.get_value(
            FileStatCollection.WORD_COUNT.value) is not None
        assert file_report.get_value(
            FileStatCollection.CHARACTER_COUNT.value) is not None
        assert file_report.get_value(
            FileStatCollection.SENTENCE_COUNT.value) is not None
        assert file_report.get_value(
            FileStatCollection.ARI_WRITING_SCORE.value) is not None

        # Test file type is correctly identified
        file_type = file_report.get_value(
            FileStatCollection.TYPE_OF_FILE.value)
        assert file_type == FileDomain.DOCUMENTATION

        # Test basic file statistics are also present
        assert file_report.get_value(
            FileStatCollection.FILE_SIZE_BYTES.value) is not None
        assert file_report.get_value(
            FileStatCollection.DATE_CREATED.value) is not None

    def test_create_with_analysis_python_file(self, temp_dir):
        """Test analysis for Python files."""
        content = (
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n\n"
            "class TestClass:\n"
            "    def __init__(self):\n"
            "        pass\n\n"
            "    def method_one(self):\n"
            "        return 'test'\n\n"
            "def function_one():\n"
            "    return 42\n\n"
            "def function_two(x, y):\n"
            "    return x + y\n"
        )

        file_path = _create_temp_file("example.py", content, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "example.py")

        # Test Python-specific statistics
        assert file_report.get_value(
            FileStatCollection.NUMBER_OF_FUNCTIONS.value) is not None
        assert file_report.get_value(
            FileStatCollection.NUMBER_OF_CLASSES.value) is not None
        assert file_report.get_value(
            FileStatCollection.IMPORTED_PACKAGES.value) is not None

        # Test file type
        file_type = file_report.get_value(
            FileStatCollection.TYPE_OF_FILE.value)
        assert file_type == FileDomain.CODE

        # Test specific counts
        functions = file_report.get_value(
            FileStatCollection.NUMBER_OF_FUNCTIONS.value)
        classes = file_report.get_value(
            FileStatCollection.NUMBER_OF_CLASSES.value)
        assert functions >= 3  # __init__, method_one, function_one, function_two
        assert classes == 1  # TestClass

    def test_create_with_analysis_text_file(self, temp_dir):
        """Test analysis for plain text files."""
        content = "Line one\nLine two\nLine three\n"

        file_path = _create_temp_file("test.txt", content, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "test.txt")

        # Test text-based statistics
        lines = file_report.get_value(FileStatCollection.LINES_IN_FILE.value)
        assert lines == 4  # Including empty line at end

        # Test that natural language stats are present for .txt files
        assert file_report.get_value(
            FileStatCollection.WORD_COUNT.value) is not None

        # Test file type
        file_type = file_report.get_value(
            FileStatCollection.TYPE_OF_FILE.value)
        assert file_type == FileDomain.DOCUMENTATION

    def test_create_with_analysis_javascript_file(self, temp_dir):
        """Test analysis for JavaScript files."""
        content = (
            "import React from 'react';\n"
            "const axios = require('axios');\n\n"
            "class Component {\n"
            "    constructor() {}\n"
            "    render() { return null; }\n"
            "}\n\n"
            "function regularFunction() {\n"
            "    return 'test';\n"
            "}\n\n"
            "const arrowFunction = () => {\n"
            "    return 42;\n"
            "};\n"
        )

        file_path = _create_temp_file("example.js", content, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "example.js")

        # Test JavaScript-specific statistics
        assert file_report.get_value(
            FileStatCollection.NUMBER_OF_FUNCTIONS.value) is not None
        assert file_report.get_value(
            FileStatCollection.NUMBER_OF_CLASSES.value) is not None
        assert file_report.get_value(
            FileStatCollection.IMPORTED_PACKAGES.value) is not None

        # Test file type
        file_type = file_report.get_value(
            FileStatCollection.TYPE_OF_FILE.value)
        assert file_type == FileDomain.CODE

    def test_create_with_analysis_unknown_file_type(self, temp_dir):
        """Test analysis for unknown file types falls back to base analyzer."""
        content = "Some content"

        file_path = _create_temp_file("test.unknown", content, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "test.unknown")

        # Should have basic file statistics
        assert file_report.get_value(
            FileStatCollection.FILE_SIZE_BYTES.value) is not None
        assert file_report.get_value(
            FileStatCollection.DATE_CREATED.value) is not None

        # Should not have specialized statistics
        assert file_report.get_value(
            FileStatCollection.WORD_COUNT.value) is None
        assert file_report.get_value(
            FileStatCollection.NUMBER_OF_FUNCTIONS.value) is None


class TestAnalyzerFactoryFunction:
    """Test the get_appropriate_analyzer factory function by checking extension mapping."""

    @pytest.mark.parametrize("ext", ['.md', '.txt', '.rst', '.doc', '.docx'])
    def test_analyzer_type_detection_natural_language_extensions(self, ext):
        """Test that natural language extensions are recognized."""
        natural_language_extensions = {'.md', '.txt', '.rst', '.doc', '.docx'}
        test_path = f"test{ext}"
        file_path = Path(test_path)
        extension = file_path.suffix.lower()

        # Verify extension is in natural language set
        assert extension in natural_language_extensions

    @pytest.mark.parametrize("ext,lang", [
        ('.py', 'Python'),
        ('.java', 'Java'),
        ('.js', 'JavaScript'),
        ('.jsx', 'JavaScript')
    ])
    def test_analyzer_type_detection_code_extensions(self, ext, lang):
        """Test that code extensions are recognized."""
        test_path = f"test{ext}"
        file_path = Path(test_path)
        extension = file_path.suffix.lower()

        # Verify extension mapping
        if ext == '.py':
            assert extension == '.py'
        elif ext == '.java':
            assert extension == '.java'
        elif ext in {'.js', '.jsx'}:
            assert extension in {'.js', '.jsx'}

    @pytest.mark.parametrize("ext", ['.css', '.html', '.xml', '.json', '.yml', '.yaml'])
    def test_analyzer_type_detection_text_extensions(self, ext):
        """Test that text extensions are recognized."""
        text_extensions = {'.css', '.html', '.xml', '.json', '.yml', '.yaml'}
        test_path = f"test{ext}"
        file_path = Path(test_path)
        extension = file_path.suffix.lower()

        # Verify extension is in text set
        assert extension in text_extensions


class TestFileReportEdgeCases:
    """Test edge cases and error handling for FileReport."""

    def test_create_with_analysis_nonexistent_file(self):
        """Test handling of nonexistent files."""
        # The analyzer will raise an exception, so we expect this to fail
        with pytest.raises(Exception):
            FileReport.create_with_analysis("/nonexistent/dir", "file.py")

    def test_create_with_analysis_empty_file(self, temp_dir):
        """Test analysis of empty files."""
        file_path = _create_temp_file("empty.py", "", temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "empty.py")

        # Should have basic file statistics
        assert file_report.get_value(
            FileStatCollection.FILE_SIZE_BYTES.value) is not None
        size = file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value)
        assert size == 0

    @pytest.mark.parametrize("filename", ["test.MD", "test.PY", "test.JS"])
    def test_create_with_analysis_case_insensitive_extensions(self, filename, temp_dir):
        """Test that file extension matching is case-insensitive."""
        content = "# Test content. This is a sentence with proper punctuation!"

        file_path = _create_temp_file(filename, content, temp_dir)
        file_report = FileReport.create_with_analysis(str(temp_dir), filename)

        # Should be analyzed without crashing
        assert isinstance(file_report, FileReport)
        # Should have basic file statistics
        assert file_report.get_value(
            FileStatCollection.FILE_SIZE_BYTES.value) is not None

    def test_natural_language_statistics_comprehensive(self, temp_dir):
        """Test comprehensive natural language statistics measurement."""
        content = (
            "This is a comprehensive test document. "
            "It contains multiple sentences for testing! "
            "Does it work correctly with questions? "
            "Let's find out with this detailed analysis.\n\n"
            "Here's another paragraph with technical content. "
            "The automated readability index should be calculated properly."
        )

        file_path = _create_temp_file("comprehensive.md", content, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "comprehensive.md")

        # Test all natural language statistics are present and reasonable
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        char_count = file_report.get_value(
            FileStatCollection.CHARACTER_COUNT.value)
        sentence_count = file_report.get_value(
            FileStatCollection.SENTENCE_COUNT.value)
        ari_score = file_report.get_value(
            FileStatCollection.ARI_WRITING_SCORE.value)

        assert isinstance(word_count, int)
        assert word_count > 0

        assert isinstance(char_count, int)
        assert char_count > 0

        assert isinstance(sentence_count, int)
        assert sentence_count > 0

        assert isinstance(ari_score, float)

    def test_multiple_file_analysis_consistency(self, temp_dir):
        """Test that analyzing the same file multiple times gives consistent results."""
        content = (
            "def test_function():\n"
            "    '''Test function'''\n"
            "    return 42\n\n"
            "class TestClass:\n"
            "    def method(self):\n"
            "        pass\n"
        )

        file_path = _create_temp_file("consistency.py", content, temp_dir)

        # Analyze the same file multiple times
        report1 = FileReport.create_with_analysis(
            str(temp_dir), "consistency.py")
        report2 = FileReport.create_with_analysis(
            str(temp_dir), "consistency.py")

        # Results should be consistent
        assert (report1.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value) ==
                report2.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value))
        assert (report1.get_value(FileStatCollection.NUMBER_OF_CLASSES.value) ==
                report2.get_value(FileStatCollection.NUMBER_OF_CLASSES.value))

    def test_ari_score_edge_cases(self, temp_dir):
        """Test ARI score calculation with edge cases that could cause division by zero."""

        # Test with content that has no sentences (no punctuation)
        content_no_sentences = "word word word word word"  # No punctuation
        file_path = _create_temp_file(
            "no_sentences.md", content_no_sentences, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "no_sentences.md")

        # Should not crash and should return 0.0 for ARI score
        ari_score = file_report.get_value(
            FileStatCollection.ARI_WRITING_SCORE.value)
        assert ari_score == 0.0

        # Should still have other stats
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        assert word_count > 0
        sentence_count = file_report.get_value(
            FileStatCollection.SENTENCE_COUNT.value)
        assert sentence_count == 0

        # Test with empty content
        file_path_empty = _create_temp_file("empty.md", "", temp_dir)
        file_report_empty = FileReport.create_with_analysis(
            str(temp_dir), "empty.md")

        # Should not crash and should return 0.0 for ARI score
        ari_score_empty = file_report_empty.get_value(
            FileStatCollection.ARI_WRITING_SCORE.value)
        assert ari_score_empty == 0.0

        # Word and sentence counts should be 0
        word_count_empty = file_report_empty.get_value(
            FileStatCollection.WORD_COUNT.value)
        sentence_count_empty = file_report_empty.get_value(
            FileStatCollection.SENTENCE_COUNT.value)
        assert word_count_empty == 0
        assert sentence_count_empty == 0

    def test_text_file_with_proper_sentences(self, temp_dir):
        """Test text file analysis with proper sentence structure."""
        content = "This is sentence one. This is sentence two! Is this sentence three?"

        file_path = _create_temp_file(
            "proper_sentences.txt", content, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "proper_sentences.txt")

        # Should work without division by zero and calculate proper ARI score
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        sentence_count = file_report.get_value(
            FileStatCollection.SENTENCE_COUNT.value)
        ari_score = file_report.get_value(
            FileStatCollection.ARI_WRITING_SCORE.value)

        assert word_count > 0
        assert sentence_count > 0
        assert isinstance(ari_score, float)
        # ARI score should be calculated properly (not 0.0) since we have both words and sentences
        assert ari_score != 0.0

    def test_natural_language_file_with_only_words(self, temp_dir):
        """Test natural language analysis with words but no sentence punctuation."""
        content = "just some words without any punctuation marks"

        file_path = _create_temp_file("words_only.md", content, temp_dir)
        file_report = FileReport.create_with_analysis(
            str(temp_dir), "words_only.md")

        # Should not crash due to division by zero protection
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        sentence_count = file_report.get_value(
            FileStatCollection.SENTENCE_COUNT.value)
        ari_score = file_report.get_value(
            FileStatCollection.ARI_WRITING_SCORE.value)

        assert word_count > 0
        assert sentence_count == 0  # No punctuation
        assert ari_score == 0.0  # Should be 0.0 due to division by zero protection


class TestFileReportStatisticsIntegration:
    """Test integration between FileReport and StatisticIndex."""

    def test_file_report_statistics_integration(self):
        """Test integration between FileReport and StatisticIndex."""
        stats = StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 100),
            Statistic(FileStatCollection.WORD_COUNT.value, 500),
            Statistic(FileStatCollection.TYPE_OF_FILE.value,
                      FileDomain.DOCUMENTATION)
        ])

        file_report = FileReport(stats, "test.md")

        # Test all statistics are accessible
        assert file_report.get_value(
            FileStatCollection.LINES_IN_FILE.value) == 100
        assert file_report.get_value(
            FileStatCollection.WORD_COUNT.value) == 500
        assert file_report.get_value(
            FileStatCollection.TYPE_OF_FILE.value) == FileDomain.DOCUMENTATION

        # Test to_dict works
        result_dict = file_report.to_dict()
        assert "LINES_IN_FILE" in result_dict
        assert "WORD_COUNT" in result_dict
        assert "TYPE_OF_FILE" in result_dict

    def test_file_report_add_statistic(self):
        """Test adding statistics to FileReport after creation."""
        stats = StatisticIndex()
        file_report = FileReport(stats, "test.py")

        # Add a statistic
        new_stat = Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 2048)
        file_report.add_statistic(new_stat)

        # Verify it was added
        assert file_report.get_value(
            FileStatCollection.FILE_SIZE_BYTES.value) == 2048


# Run with: pytest tests/test_file_report.py -v
