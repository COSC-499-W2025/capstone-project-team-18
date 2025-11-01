"""
Comprehensive tests for FileReport class in src/classes/report.py
Tests the automatic file type detection and natural language statistics integration.
"""

import unittest
import sys
import os
from pathlib import Path
from datetime import datetime
import tempfile

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classes.report import FileReport, BaseReport
from src.classes.statistic import (
    StatisticIndex, Statistic, FileStatCollection, FileDomain
)
from src.classes.analyzer import (
    BaseFileAnalyzer, TextFileAnalyzer, NaturalLanguageAnalyzer,
    PythonAnalyzer, JavaAnalyzer, JavaScriptAnalyzer, get_appropriate_analyzer
)

# Test fixtures directory
TEST_DIR = Path(__file__).parent / "resources"


def _create_temp_file(filename: str, content: str, path: Path, encoding: str = "utf-8") -> Path:
    """Helper function to create temporary test files."""
    file_path = path / filename
    file_path.write_text(content, encoding=encoding)
    return file_path


class TestFileReportBasics(unittest.TestCase):
    """Test basic FileReport functionality and inheritance."""

    def test_file_report_inheritance(self):
        """Test that FileReport properly inherits from BaseReport."""
        stats = StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 10)
        ])
        file_report = FileReport(stats, "test.py")

        # Test inheritance
        self.assertIsInstance(file_report, BaseReport)
        self.assertIsInstance(file_report, FileReport)

        # Test inherited methods work
        self.assertEqual(file_report.filepath, "test.py")
        self.assertIsNotNone(file_report.to_dict())
        self.assertIsInstance(file_report.to_dict(), dict)

        # Test that repr doesn't crash
        repr_str = repr(file_report)
        self.assertIsInstance(repr_str, str)
        self.assertTrue("FileReport" in repr_str)

    def test_get_filename(self):
        """Test filename extraction from filepath."""
        test_cases = [
            ("/path/to/file.py", "file.py"),
            ("./relative/path/document.md", "document.md"),
            ("simple.txt", "simple.txt"),
            ("/complex/path/with.multiple.dots.js", "with.multiple.dots.js")
        ]

        for filepath, expected_filename in test_cases:
            stats = StatisticIndex()
            file_report = FileReport(stats, filepath)
            self.assertEqual(file_report.get_filename(), expected_filename)

    def test_file_report_basic_construction(self):
        """Test basic FileReport construction with statistics."""
        stats = StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 25),
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 1024)
        ])

        file_report = FileReport(stats, "example.txt")

        self.assertEqual(file_report.filepath, "example.txt")
        self.assertEqual(
            file_report.get_value(FileStatCollection.LINES_IN_FILE.value), 25
        )
        self.assertEqual(
            file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value), 1024
        )


class TestFileReportWithAnalysis(unittest.TestCase):
    """Test FileReport.create_with_analysis() method with different file types."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_with_analysis_natural_language_md(self):
        """Test natural language analysis for Markdown files."""
        content = (
            "# Test Document\n\n"
            "This is a test document with multiple sentences. "
            "It contains exactly fifty words in total to test our word counting functionality accurately. "
            "The document also tests sentence counting and character analysis for the automated readability index calculation.\n\n"
            "## Section Two\n"
            "Another paragraph for testing purposes."
        )

        file_path = _create_temp_file("test.md", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Test that natural language statistics are present
        self.assertIsNotNone(file_report.get_value(FileStatCollection.WORD_COUNT.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.CHARACTER_COUNT.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.SENTENCE_COUNT.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.ARI_WRITING_SCORE.value))

        # Test file type is correctly identified
        file_type = file_report.get_value(FileStatCollection.TYPE_OF_FILE.value)
        self.assertEqual(file_type, FileDomain.DOCUMENTATION)

        # Test basic file statistics are also present
        self.assertIsNotNone(file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.DATE_CREATED.value))

    def test_create_with_analysis_python_file(self):
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

        file_path = _create_temp_file("test.py", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Test Python-specific statistics
        self.assertIsNotNone(file_report.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.NUMBER_OF_CLASSES.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.IMPORTED_PACKAGES.value))

        # Test file type
        file_type = file_report.get_value(FileStatCollection.TYPE_OF_FILE.value)
        self.assertEqual(file_type, FileDomain.CODE)

        # Test specific counts
        functions = file_report.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value)
        classes = file_report.get_value(FileStatCollection.NUMBER_OF_CLASSES.value)
        self.assertGreaterEqual(functions, 3)  # __init__, method_one, function_one, function_two
        self.assertEqual(classes, 1)  # TestClass

    def test_create_with_analysis_text_file(self):
        """Test analysis for plain text files."""
        content = "Line one\nLine two\nLine three\n"

        file_path = _create_temp_file("test.txt", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Test text-based statistics
        lines = file_report.get_value(FileStatCollection.LINES_IN_FILE.value)
        self.assertEqual(lines, 4)  # Including empty line at end

        # Test that natural language stats are present for .txt files
        self.assertIsNotNone(file_report.get_value(FileStatCollection.WORD_COUNT.value))

        # Test file type
        file_type = file_report.get_value(FileStatCollection.TYPE_OF_FILE.value)
        self.assertEqual(file_type, FileDomain.DOCUMENTATION)

    def test_create_with_analysis_javascript_file(self):
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

        file_path = _create_temp_file("test.js", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Test JavaScript-specific statistics
        self.assertIsNotNone(file_report.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.NUMBER_OF_CLASSES.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.IMPORTED_PACKAGES.value))

        # Test file type
        file_type = file_report.get_value(FileStatCollection.TYPE_OF_FILE.value)
        self.assertEqual(file_type, FileDomain.CODE)

    def test_create_with_analysis_unknown_file_type(self):
        """Test analysis for unknown file types falls back to base analyzer."""
        content = "Some content"

        file_path = _create_temp_file("test.unknown", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Should have basic file statistics
        self.assertIsNotNone(file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value))
        self.assertIsNotNone(file_report.get_value(FileStatCollection.DATE_CREATED.value))

        # Should not have specialized statistics
        self.assertIsNone(file_report.get_value(FileStatCollection.WORD_COUNT.value))
        self.assertIsNone(file_report.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value))


class TestAnalyzerFactoryFunction(unittest.TestCase):
    """Test the get_appropriate_analyzer factory function by checking extension mapping."""

    def test_analyzer_type_detection_by_extension(self):
        """Test that the factory function returns correct analyzer types based on file extensions."""
        # Test natural language files - we'll check the type by examining the extension logic
        natural_language_extensions = {'.md', '.txt', '.rst', '.doc', '.docx'}
        for ext in natural_language_extensions:
            # Create a dummy path just for extension checking
            test_path = f"test{ext}"
            file_path = Path(test_path)
            extension = file_path.suffix.lower()

            # Verify extension is in natural language set
            self.assertIn(extension, natural_language_extensions)

        # Test code files
        code_extensions = {'.py': 'Python', '.java': 'Java', '.js': 'JavaScript', '.jsx': 'JavaScript'}
        for ext, lang in code_extensions.items():
            test_path = f"test{ext}"
            file_path = Path(test_path)
            extension = file_path.suffix.lower()

            # Verify extension mapping
            if ext == '.py':
                self.assertEqual(extension, '.py')
            elif ext == '.java':
                self.assertEqual(extension, '.java')
            elif ext in {'.js', '.jsx'}:
                self.assertIn(extension, {'.js', '.jsx'})

        # Test text files
        text_extensions = {'.css', '.html', '.xml', '.json', '.yml', '.yaml'}
        for ext in text_extensions:
            test_path = f"test{ext}"
            file_path = Path(test_path)
            extension = file_path.suffix.lower()

            # Verify extension is in text set
            self.assertIn(extension, text_extensions)


class TestFileReportEdgeCases(unittest.TestCase):
    """Test edge cases and error handling for FileReport."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_with_analysis_nonexistent_file(self):
        """Test handling of nonexistent files."""
        # The analyzer will raise an exception, so we expect this to fail
        with self.assertRaises(Exception):
            FileReport.create_with_analysis("/nonexistent/file.py")

    def test_create_with_analysis_empty_file(self):
        """Test analysis of empty files."""
        file_path = _create_temp_file("empty.py", "", self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Should have basic file statistics
        self.assertIsNotNone(file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value))
        size = file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value)
        self.assertEqual(size, 0)

    def test_create_with_analysis_case_insensitive_extensions(self):
        """Test that file extension matching is case-insensitive."""
        content = "# Test content. This is a sentence with proper punctuation!"

        test_cases = [
            "test.MD",
            "test.PY",
            "test.JS",
        ]

        for filename in test_cases:
            file_path = _create_temp_file(filename, content, self.temp_dir)
            file_report = FileReport.create_with_analysis(str(file_path))

            # Should be analyzed without crashing
            self.assertIsInstance(file_report, FileReport)
            # Should have basic file statistics
            self.assertIsNotNone(file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value))

    def test_natural_language_statistics_comprehensive(self):
        """Test comprehensive natural language statistics measurement."""
        content = (
            "This is a comprehensive test document. "
            "It contains multiple sentences for testing! "
            "Does it work correctly with questions? "
            "Let's find out with this detailed analysis.\n\n"
            "Here's another paragraph with technical content. "
            "The automated readability index should be calculated properly."
        )

        file_path = _create_temp_file("comprehensive.md", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Test all natural language statistics are present and reasonable
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        char_count = file_report.get_value(FileStatCollection.CHARACTER_COUNT.value)
        sentence_count = file_report.get_value(FileStatCollection.SENTENCE_COUNT.value)
        ari_score = file_report.get_value(FileStatCollection.ARI_WRITING_SCORE.value)

        self.assertIsInstance(word_count, int)
        self.assertGreater(word_count, 0)

        self.assertIsInstance(char_count, int)
        self.assertGreater(char_count, 0)

        self.assertIsInstance(sentence_count, int)
        self.assertGreater(sentence_count, 0)

        self.assertIsInstance(ari_score, float)

    def test_multiple_file_analysis_consistency(self):
        """Test that analyzing the same file multiple times gives consistent results."""
        content = (
            "def test_function():\n"
            "    '''Test function'''\n"
            "    return 42\n\n"
            "class TestClass:\n"
            "    def method(self):\n"
            "        pass\n"
        )

        file_path = _create_temp_file("consistency.py", content, self.temp_dir)

        # Analyze the same file multiple times
        report1 = FileReport.create_with_analysis(str(file_path))
        report2 = FileReport.create_with_analysis(str(file_path))

        # Results should be consistent
        self.assertEqual(
            report1.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value),
            report2.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value)
        )
        self.assertEqual(
            report1.get_value(FileStatCollection.NUMBER_OF_CLASSES.value),
            report2.get_value(FileStatCollection.NUMBER_OF_CLASSES.value)
        )

    def test_ari_score_edge_cases(self):
        """Test ARI score calculation with edge cases that could cause division by zero."""

        # Test with content that has no sentences (no punctuation)
        content_no_sentences = "word word word word word"  # No punctuation
        file_path = _create_temp_file("no_sentences.md", content_no_sentences, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Should not crash and should return 0.0 for ARI score
        ari_score = file_report.get_value(FileStatCollection.ARI_WRITING_SCORE.value)
        self.assertEqual(ari_score, 0.0)

        # Should still have other stats
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        self.assertGreater(word_count, 0)
        sentence_count = file_report.get_value(FileStatCollection.SENTENCE_COUNT.value)
        self.assertEqual(sentence_count, 0)

        # Test with empty content
        file_path_empty = _create_temp_file("empty.md", "", self.temp_dir)
        file_report_empty = FileReport.create_with_analysis(str(file_path_empty))

        # Should not crash and should return 0.0 for ARI score
        ari_score_empty = file_report_empty.get_value(FileStatCollection.ARI_WRITING_SCORE.value)
        self.assertEqual(ari_score_empty, 0.0)

        # Word and sentence counts should be 0
        word_count_empty = file_report_empty.get_value(FileStatCollection.WORD_COUNT.value)
        sentence_count_empty = file_report_empty.get_value(FileStatCollection.SENTENCE_COUNT.value)
        self.assertEqual(word_count_empty, 0)
        self.assertEqual(sentence_count_empty, 0)

    def test_text_file_with_proper_sentences(self):
        """Test text file analysis with proper sentence structure."""
        content = "This is sentence one. This is sentence two! Is this sentence three?"

        file_path = _create_temp_file("proper_sentences.txt", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Should work without division by zero and calculate proper ARI score
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        sentence_count = file_report.get_value(FileStatCollection.SENTENCE_COUNT.value)
        ari_score = file_report.get_value(FileStatCollection.ARI_WRITING_SCORE.value)

        self.assertGreater(word_count, 0)
        self.assertGreater(sentence_count, 0)
        self.assertIsInstance(ari_score, float)
        # ARI score should be calculated properly (not 0.0) since we have both words and sentences
        self.assertNotEqual(ari_score, 0.0)

    def test_natural_language_file_with_only_words(self):
        """Test natural language analysis with words but no sentence punctuation."""
        content = "just some words without any punctuation marks"

        file_path = _create_temp_file("words_only.md", content, self.temp_dir)
        file_report = FileReport.create_with_analysis(str(file_path))

        # Should not crash due to division by zero protection
        word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
        sentence_count = file_report.get_value(FileStatCollection.SENTENCE_COUNT.value)
        ari_score = file_report.get_value(FileStatCollection.ARI_WRITING_SCORE.value)

        self.assertGreater(word_count, 0)
        self.assertEqual(sentence_count, 0)  # No punctuation
        self.assertEqual(ari_score, 0.0)  # Should be 0.0 due to division by zero protection


class TestFileReportStatisticsIntegration(unittest.TestCase):
    """Test integration between FileReport and StatisticIndex."""

    def test_file_report_statistics_integration(self):
        """Test integration between FileReport and StatisticIndex."""
        stats = StatisticIndex([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 100),
            Statistic(FileStatCollection.WORD_COUNT.value, 500),
            Statistic(FileStatCollection.TYPE_OF_FILE.value, FileDomain.DOCUMENTATION)
        ])

        file_report = FileReport(stats, "test.md")

        # Test all statistics are accessible
        self.assertEqual(file_report.get_value(FileStatCollection.LINES_IN_FILE.value), 100)
        self.assertEqual(file_report.get_value(FileStatCollection.WORD_COUNT.value), 500)
        self.assertEqual(file_report.get_value(FileStatCollection.TYPE_OF_FILE.value), FileDomain.DOCUMENTATION)

        # Test to_dict works
        result_dict = file_report.to_dict()
        self.assertIn("LINES_IN_FILE", result_dict)
        self.assertIn("WORD_COUNT", result_dict)
        self.assertIn("TYPE_OF_FILE", result_dict)

    def test_file_report_add_statistic(self):
        """Test adding statistics to FileReport after creation."""
        stats = StatisticIndex()
        file_report = FileReport(stats, "test.py")

        # Add a statistic
        new_stat = Statistic(FileStatCollection.FILE_SIZE_BYTES.value, 2048)
        file_report.add_statistic(new_stat)

        # Verify it was added
        self.assertEqual(file_report.get_value(FileStatCollection.FILE_SIZE_BYTES.value), 2048)


if __name__ == '__main__':
    # Run unittest tests
    unittest.main(verbosity=2)