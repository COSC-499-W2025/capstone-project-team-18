"""
Tests for analyzer classes in src/classes/analyzer.py
"""

from pathlib import Path
from datetime import datetime
import pytest
from src.classes.analyzer import *
from src.classes.statistic import FileStatCollection, CodingLanguage
from src.utils.project_discovery import ProjectFiles
from src.utils.zipped_utils import unzip_file
from conftest import _create_temp_file, RESOURCE_DIR


def test_base_file_analyzer_process_returns_file_report_with_core_stats(temp_text_file: list[str]):
    '''
    Test that the metadata of the file we created in `temp_text_file()` will be read and stored
    in a `FileReport` object by the `analyze()` function.
    '''
    analyzer = BaseFileAnalyzer(temp_text_file[0], temp_text_file[1])
    report = analyzer.analyze()  # FileReport obj
    # Check that filepath is stored in report obj
    assert getattr(report, "filepath") == temp_text_file[1]

    # Core stats exist
    size = report.get_value(FileStatCollection.FILE_SIZE_BYTES.value)
    created = report.get_value(FileStatCollection.DATE_CREATED.value)
    modified = report.get_value(FileStatCollection.DATE_MODIFIED.value)

    # Validate types and basic expectations
    assert isinstance(size, int) and size > 0
    assert isinstance(created, datetime.datetime)
    assert isinstance(modified, datetime.datetime)

    # Size should match the actual file size
    assert size == Path(
        temp_text_file[0] + '/' + temp_text_file[1]).stat().st_size


def test_base_file_analyzer_nonexistent_file_logs_and_returns_empty():
    '''
    Test that the `analyze()` throws error for a non-existent file
    '''
    fake_file = "does_not_exist.xyz"
    analyzer = BaseFileAnalyzer("", fake_file)

    with pytest.raises(Exception):
        analyzer.analyze()


def test_extract_file_reports_recieves_empty_project(tmp_path):
    """
    Test that the extraction returns None upon reciept of an empty project directory
    """

    project_discovery = None

    listReport = extract_file_reports(project_discovery)
    assert listReport is None


def test_extract_file_reports_returns_project(tmp_path):
    """
    Test that the extraction returns a list of FileReports with the accurate # of reports
    """

    files = ["t1est1.txt", "test2.txt", "test3.txt", "test4.txt", "test5.txt"]

    for filename in files:
        _create_temp_file(filename, "Sample content", tmp_path)

    project_file = ProjectFiles(
        name="TestProject",
        root_path=str(tmp_path),
        file_paths=files,
        repo=None
    )

    listReport = extract_file_reports(project_file)
    assert listReport is not None
    assert len(listReport) == 5 and all(isinstance(report, FileReport)
                                        for report in listReport)


def test_created_modifiyed_and_accessed_dates(tmp_path):
    """
    Tests that for a file, we have that the date created
    is the earliest date, then date modifiyed, then
    date accessed
    """

    unzip_file("tests/resources/mac_projects.zip", tmp_path)

    file_path = tmp_path / "Projects" / "ProjectA" / "a_1.txt"

    report = BaseFileAnalyzer(str(file_path.parent), file_path.name).analyze()

    date_modified = report.get_value(FileStatCollection.DATE_MODIFIED.value)
    date_created = report.get_value(FileStatCollection.DATE_CREATED.value)

    assert date_created <= date_modified


def test_extract_file_reports_recieves_project_with_subfolder(tmp_path):
    """
    Test that the extraction returns a list of FileReports with the accurate #
    """

    _create_temp_file("a_1.txt", "File One", tmp_path)
    _create_temp_file("a_2.txt", "File Two", tmp_path)
    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()
    _create_temp_file("a_3.txt", "File Three", subfolder)

    project_file = ProjectFiles(
        name="ProjectA",
        root_path=str(tmp_path),
        file_paths=["a_1.txt", "a_2.txt", "subfolder/a_3.txt"],
        repo=None
    )

    listReport = extract_file_reports(project_file)

    # print(listReport)
    assert listReport is not None
    assert len(listReport) == 3 and all(isinstance(report, FileReport)
                                        for report in listReport)

# ---------- Test TextFileAnalyzer ----------


def test_text_file_reading_many_encodings(tmp_path: Path):
    """
    Test that TextFileAnalyzer can correctly read files written in common encoding types.
    """
    encoding_types = ["utf-8", "latin-1", "iso-8859-1", "utf-16", "ascii"]

    content = (
        "Please be able to read me and my special characters!\n"
        "!@#$%^&*()_+|}{\":?></.,';\\][-]0987654321`~"
    )

    for encoding in encoding_types:
        file_path = _create_temp_file(
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


def test_count_lines(tmp_path: Path):
    """
    Test that with a normal file, TextFileAnalyzer can correctly count lines.
    """
    content = (
        "Here is my file\n"
        "it has\n"
        "\n"
        "5 lines!\n"
    )

    file_path = _create_temp_file("test_count_lines.txt", content, tmp_path)
    report = TextFileAnalyzer(file_path[0], file_path[1]).analyze()

    line_count = report.get_value(FileStatCollection.LINES_IN_FILE.value)
    assert line_count == 5


def test_count_no_lines(tmp_path: Path):
    """
    Test that TextFileAnalyzer correctly handles empty files.
    """
    file_path = _create_temp_file("test_count_no_lines.txt", "", tmp_path)
    report = TextFileAnalyzer(file_path[0], file_path[1]).analyze()

    line_count = report.get_value(FileStatCollection.LINES_IN_FILE.value)
    assert line_count == 1


def test_many_lines(tmp_path: Path):
    """
    Test that TextFileAnalyzer counts many different lines.
    """

    file_path = _create_temp_file(
        "test_count_no_lines.txt", "\n" * 999, tmp_path)
    report = TextFileAnalyzer(file_path[0], file_path[1]).analyze()

    line_count = report.get_value(FileStatCollection.LINES_IN_FILE.value)
    assert line_count == 1000

# ---------- Test NaturalLanguage ----------


def test_NaturalLanguageAnalyzer_core_stats(tmp_path: Path):

    content = (
        "# Welcome"
        "\n"
        "## Introduction"
        "\n"
        "Hello, welcome to my test of the NaturalLanguageAnalyzer. I have "
        "personally verified all the stats we are going to be testing for. "
        "This means that if the test gets something wrong, it is because some "
        "logic with the counting is wrong! Don't you love python testing? Here are "
        "some new lines to try to mess with the class."
        "\n"
        "## More Text \n"
        "Now I want to throw in another sentence!\n"
        "Here is a list of things:\n"
        "   - Yellow\n"
        "   - Red\n"
        "   - Green\n"
        "   - 1 Fish 2 Fish\n"
    )

    file_path = _create_temp_file(
        "test_NaturalLanguageAnalyzer_core_stats.md", content, tmp_path)

    report = NaturalLanguageAnalyzer(file_path[0], file_path[1]).analyze()

    REAL_WORD_COUNT = 83
    REAL_ALPHA_NUMERIC_CHARACTER_COUNT = 356
    REAL_SENTENCE_COUNT = 6
    REAL_ARI_SCORE = 4.71 * (REAL_ALPHA_NUMERIC_CHARACTER_COUNT / REAL_WORD_COUNT) + \
        0.5 * (REAL_WORD_COUNT / REAL_SENTENCE_COUNT) - 21.43
    REAL_TYPE_OF_FILE = FileDomain.DOCUMENTATION

    measured_word_count = report.get_value(FileStatCollection.WORD_COUNT.value)
    measured_character_count = report.get_value(
        FileStatCollection.CHARACTER_COUNT.value)
    measured_sentence_count = report.get_value(
        FileStatCollection.SENTENCE_COUNT.value)
    measured_ari_score = report.get_value(
        FileStatCollection.ARI_WRITING_SCORE.value)
    measured_type_of_file = report.get_value(
        FileStatCollection.TYPE_OF_FILE.value)

    assert REAL_WORD_COUNT == measured_word_count, f"Expected {REAL_WORD_COUNT}, got {measured_word_count}"
    assert REAL_ALPHA_NUMERIC_CHARACTER_COUNT == measured_character_count, f"Expected {REAL_ALPHA_NUMERIC_CHARACTER_COUNT}, got {measured_character_count}"
    assert REAL_SENTENCE_COUNT == measured_sentence_count, f"Expected {REAL_SENTENCE_COUNT}, got {measured_sentence_count}"
    assert REAL_ARI_SCORE == measured_ari_score, f"Expected {REAL_ARI_SCORE}, got {measured_ari_score}"
    assert REAL_TYPE_OF_FILE == measured_type_of_file, f"Expected {REAL_TYPE_OF_FILE}, got {measured_type_of_file}"

# ---------- Test CodingAnalyzer ---------


def test_determines_correct_coding_language(tmp_path):
    """
    Ensure that in a project with many different
    coding files, that the Statistic CODING_LANGUAGE
    is correctly recorded.
    """

    file_extensions_to_test = (
        (CodingLanguage.PYTHON, ".py"),
        (CodingLanguage.JAVA, ".java"),
        (CodingLanguage.CSHARP, ".cs"),
        (CodingLanguage.RUBY, ".rb"),
        (CodingLanguage.GO, ".go"),
        (CodingLanguage.TYPESCRIPT, ".ts")
    )

    for value, extension in file_extensions_to_test:

        path = _create_temp_file("temp" + extension, "", tmp_path)

        report = CodeFileAnalyzer(path[0], path[1]).analyze()

        assert report.get_value(
            FileStatCollection.CODING_LANGUAGE.value) == value


def test_unkown_coding_language(tmp_path):
    """
    In the situation where there is a file extension
    with no known coding language, then we don't record
    a CODING_LANGUAGE value. In theory this shouldn't
    happen because this file would never be pased down to
    the CodeFileAnalyzer class, but just in case we log it here
    """

    path = _create_temp_file("temp" + ".xyx", "", tmp_path)

    report = CodeFileAnalyzer(path[0], path[1]).analyze()

    assert report.get_value(FileStatCollection.CODING_LANGUAGE.value) == None

# ---------- Test PythonAnalyzer ----------


def test_PythonAnalyzer_core_stats():
    """
    This test uses the example_python.py file
    in the tests/resources/ directory. To ensure
    that the PythonAnalyzer is correctly measuring
    statistics about Python files.
    """

    report = PythonAnalyzer("./tests/resources", "example_python.py").analyze()

    REAL_TYPE_OF_FILE = FileDomain.CODE
    REAL_NUMBER_OF_FUNCTIONS = 7
    REAL_NUMBER_OF_CLASSES = 1
    REAL_IMPORTS = ["os", "tkinter", "Classes", "Util"]

    measured_type_of_file = report.get_value(
        FileStatCollection.TYPE_OF_FILE.value)
    measured_number_of_functions = report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    measured_number_of_classes = report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value)
    measured_imports = report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value)

    assert REAL_TYPE_OF_FILE == measured_type_of_file, f"Expected {REAL_TYPE_OF_FILE}, got {measured_type_of_file}"
    assert REAL_NUMBER_OF_FUNCTIONS == measured_number_of_functions, f"Expected {REAL_NUMBER_OF_FUNCTIONS}, got {measured_number_of_functions}"
    assert REAL_NUMBER_OF_CLASSES == measured_number_of_classes, f"Expected {REAL_NUMBER_OF_CLASSES}, got {measured_number_of_classes}"
    assert set(REAL_IMPORTS) == set(
        measured_imports), f"Expected {REAL_IMPORTS}, got {measured_imports}"


def test_PythonAnalyzer_no_functions_or_classes(tmp_path: Path):
    """
    Test that PythonAnalyzer correctly handles a Python file
    with no functions or classes.
    """

    content = (
        "# This is a simple python file\n"
        "import os\n"
        "import sys\n"
        "\n"
        "print('Hello, World!')\n"
    )

    file_path = _create_temp_file(
        "test_PythonAnalyzer_no_functions_or_classes.py", content, tmp_path)

    report = PythonAnalyzer(file_path[0], file_path[1]).analyze()

    number_of_functions = report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    number_of_classes = report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value)
    imported_packages = report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value)

    assert number_of_functions == 0, f"Expected 0 functions, got {number_of_functions}"
    assert number_of_classes == 0, f"Expected 0 classes, got {number_of_classes}"
    assert set(imported_packages) == set(
        ["os", "sys"]), f"Expected no imports, got {imported_packages}"


def test_JavaAnalyzer(tmp_path):
    """
    Test JavaAnalyzer with an actual Java file.
    """
    from src.classes.analyzer import JavaAnalyzer

    report = JavaAnalyzer(str(RESOURCE_DIR), "example_java.java").analyze()

    number_of_functions = report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    number_of_classes = report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value)
    imported_packages = report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value)

    assert number_of_functions == 8, f"Expected 8 functions, got {number_of_functions}"
    assert number_of_classes == 2, f"Expected 2 classes, got {number_of_classes}"
    assert "java" in imported_packages, f"Expected 'java' in imports, got {imported_packages}"


def test_JavaScriptAnalyzer(tmp_path):
    """
    Test JavaScriptAnalyzer with an actual JavaScript file.
    """
    from src.classes.analyzer import JavaScriptAnalyzer

    report = JavaScriptAnalyzer(
        str(RESOURCE_DIR), "example_javascript.js").analyze()

    number_of_functions = report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    number_of_classes = report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value)
    imported_packages = report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value)

    assert number_of_functions >= 4, f"Expected at least 4 functions, got {number_of_functions}"
    assert number_of_classes == 2, f"Expected 2 classes, got {number_of_classes}"
    assert "react" in imported_packages, f"Expected 'react' in imports, got {imported_packages}"
    assert "axios" in imported_packages, f"Expected 'axios' in imports, got {imported_packages}"
    assert "lodash" in imported_packages, f"Expected 'lodash' in imports, got {imported_packages}"
