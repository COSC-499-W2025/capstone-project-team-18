"""
Tests for JavaScriptAnalyzer.
"""
from src.classes.analyzer import JavaScriptAnalyzer, get_appropriate_analyzer
from src.classes.statistic import FileStatCollection, FileDomain
from conftest import RESOURCE_DIR, _create_temp_file


def test_JavaScriptAnalyzer(tmp_path):
    report = JavaScriptAnalyzer(
        str(RESOURCE_DIR), "example_javascript.js").analyze()

    number_of_functions = report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value)
    number_of_classes = report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value)
    imported_packages = report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value)

    assert number_of_functions >= 4
    assert number_of_classes == 2
    assert "react" in imported_packages
    assert "axios" in imported_packages
    assert "lodash" in imported_packages


def test_create_with_analysis_javascript_file(tmp_path):
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

    file_path = _create_temp_file("example.js", content, tmp_path)
    analyzer = get_appropriate_analyzer(file_path[0], file_path[1])
    file_report = analyzer.analyze()

    # Test JavaScript-specific statistics
    assert file_report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value) is not None
    assert file_report.get_value(
        FileStatCollection.NUMBER_OF_CLASSES.value) is not None
    assert file_report.get_value(
        FileStatCollection.IMPORTED_PACKAGES.value) is not None

    # Test file type
    file_type = file_report.get_value(FileStatCollection.TYPE_OF_FILE.value)
    assert file_type == FileDomain.CODE
