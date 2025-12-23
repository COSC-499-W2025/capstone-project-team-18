"""Tests for the :class:`SpecificCodeAnalyzer` behavior."""

from src.classes.statistic import FileStatCollection
from src.classes.analyzer import PythonAnalyzer, get_appropriate_analyzer
from tests.conftest import _create_temp_file


def test_process_not_empty_not_called_for_empty_file(tmp_path, monkeypatch):
    """
    For a code file that is empty, ensure that
    _process_not_empty method is not called and
    that the statistics are set to zero appropriately.
    """

    file_path = _create_temp_file("empty.py", "", tmp_path)

    # Instead of having the process_not_empty function run the analyzer,
    # we instead give the PythonAnalyzer this fake function so we can test
    # if was actually run.

    called = {"val": False}

    def _fake_process_not_empty(self):
        called["val"] = True

    monkeypatch.setattr(PythonAnalyzer, "_process_not_empty",
                        _fake_process_not_empty)

    report = PythonAnalyzer(file_path[0], file_path[1]).analyze()

    # Ensure _process_not_empty was NOT called for an empty file
    assert called["val"] is False

    assert report.get_value(FileStatCollection.NUMBER_OF_FUNCTIONS.value) == 0
    assert report.get_value(FileStatCollection.NUMBER_OF_CLASSES.value) == 0
    assert report.get_value(FileStatCollection.IMPORTED_PACKAGES.value) == []
    assert report.get_value(FileStatCollection.NUMBER_OF_INTERFACES.value) == 0


def test_general_coding_language_does_not_get_specific(tmp_path):
    """
    Test if we have a empty file that we don't have a specifc
    analyzer for, we do not get any statistics about function,
    classes, packages, interfaces.s
    """

    file_path = _create_temp_file("empty.R", "", tmp_path)

    report = get_appropriate_analyzer(
        file_path[0], file_path[1]).analyze()

    assert report.get_value(
        FileStatCollection.NUMBER_OF_FUNCTIONS.value) is None
    assert report.get_value(FileStatCollection.NUMBER_OF_CLASSES.value) is None
    assert report.get_value(FileStatCollection.IMPORTED_PACKAGES.value) is None
    assert report.get_value(
        FileStatCollection.NUMBER_OF_INTERFACES.value) is None
