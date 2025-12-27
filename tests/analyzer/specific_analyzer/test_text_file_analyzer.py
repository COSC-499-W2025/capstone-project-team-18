"""
Tests for TextFileAnalyzer.
"""

from pathlib import Path
from src.classes.analyzer import TextFileAnalyzer
from src.classes.statistic import FileStatCollection


def test_text_file_reading_many_encodings(tmp_path: Path, create_temp_file):
    encoding_types = ["utf-8", "latin-1", "iso-8859-1", "utf-16", "ascii"]

    content = (
        "Please be able to read me and my special characters!\n"
        "!@#$%^&*()_+|}{\":?></.,';\\][-]0987654321`~"
    )

    for encoding in encoding_types:
        file_path = create_temp_file(
            f"test_text_file_reading_many_encodings_{encoding}.txt",
            content,
            tmp_path,
            encoding=encoding,
        )

        analyzer = TextFileAnalyzer(file_path[0], file_path[1])
        analyzer.analyze()

        assert analyzer.text_content == content, (
            f"TextFileAnalyzer could not recreate content with encoding {encoding}"
        )


def test_count_lines(tmp_path: Path, create_temp_file):
    content = (
        "Here is my file\n"
        "it has\n"
        "\n"
        "5 lines!\n"
    )

    file_path = create_temp_file("test_count_lines.txt", content, tmp_path)
    report = TextFileAnalyzer(file_path[0], file_path[1]).analyze()

    line_count = report.get_value(FileStatCollection.LINES_IN_FILE.value)
    assert line_count == 5


def test_count_no_lines(tmp_path: Path, create_temp_file):
    file_path = create_temp_file("test_count_no_lines.txt", "", tmp_path)
    report = TextFileAnalyzer(file_path[0], file_path[1]).analyze()

    line_count = report.get_value(FileStatCollection.LINES_IN_FILE.value)
    assert line_count == 1


def test_many_lines(tmp_path: Path, create_temp_file):
    file_path = create_temp_file(
        "test_count_no_lines.txt", "\n" * 999, tmp_path)
    report = TextFileAnalyzer(file_path[0], file_path[1]).analyze()

    line_count = report.get_value(FileStatCollection.LINES_IN_FILE.value)
    assert line_count == 1000
