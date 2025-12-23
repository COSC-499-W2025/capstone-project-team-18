"""
Tests for PythonAnalyzer.
"""
import shutil
from src.classes.analyzer import PythonAnalyzer
from src.classes.statistic import FileStatCollection, FileDomain
from tests.conftest import _create_temp_file


def test_PythonAnalyzer_core_stats(tmp_path):
    target_dir = tmp_path / "example_python"
    target_dir.mkdir()

    target_file = str(target_dir) + "/example_python.py"

    shutil.copyfile(src="./tests/resources/example_python.py",
                    dst=target_file)

    report = PythonAnalyzer(str(target_dir), "example_python.py").analyze()

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

    assert REAL_TYPE_OF_FILE == measured_type_of_file
    assert REAL_NUMBER_OF_FUNCTIONS == measured_number_of_functions
    assert REAL_NUMBER_OF_CLASSES == measured_number_of_classes
    assert set(REAL_IMPORTS) == set(measured_imports)


def test_PythonAnalyzer_no_functions_or_classes(tmp_path):
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

    assert number_of_functions == 0
    assert number_of_classes == 0
    assert set(imported_packages) == set(["os", "sys"])


def test_create_with_analysis_python_file(tmp_path):
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

    file_path = _create_temp_file("example.py", content, tmp_path)
    file_report = PythonAnalyzer(file_path[0], file_path[1]).analyze()

    # Test Python-specific statistics
    assert file_report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value) is not None
    assert file_report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value) is not None
    assert file_report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value) is not None

    # Test file type
    file_type = file_report.get_value(FileStatCollection.TYPE_OF_FILE.value)
    assert file_type == FileDomain.CODE

    # Test specific counts
    functions = file_report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    classes = file_report.get_value(FileStatCollection.NUMBER_OF_CLASSES.value)
    assert functions >= 3  # __init__, method_one, function_one, function_two
    assert classes == 1  # TestClass
