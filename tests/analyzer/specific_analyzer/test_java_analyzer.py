"""
Tests for JavaAnalyzer.
"""
from src.classes.analyzer import JavaAnalyzer
from src.classes.statistic import FileStatCollection
from conftest import RESOURCE_DIR


def test_JavaAnalyzer(tmp_path):
    report = JavaAnalyzer(str(RESOURCE_DIR), "example_java.java").analyze()

    number_of_functions = report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    number_of_classes = report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value)
    imported_packages = report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value)

    assert number_of_functions == 8
    assert number_of_classes == 2
    assert "java" in imported_packages
