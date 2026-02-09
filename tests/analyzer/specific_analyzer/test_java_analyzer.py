"""
Tests for JavaAnalyzer.
"""
from src.core.analyzer import JavaAnalyzer
from src.core.statistic import FileStatCollection


def test_JavaAnalyzer(tmp_path, resource_dir, get_ready_specific_analyzer):
    report = get_ready_specific_analyzer(
        str(resource_dir), "example_java.java").analyze()

    number_of_functions = report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    number_of_classes = report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value)
    imported_packages = report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value)

    assert number_of_functions == 8
    assert number_of_classes == 2
    assert "java" in imported_packages
