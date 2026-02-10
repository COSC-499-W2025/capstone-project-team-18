from pathlib import Path

from src.core.report import ProjectReport
from src.core.report.project.project_statistics import CodingLanguageRatio
from src.core.statistic import CodingLanguage, ProjectStatCollection


def test_coding_ratio_in_normal_project(tmp_path, get_ready_specific_analyzer):
    """
    Tests that we have approiate coding ratio
    of files
    """

    files = ["file.c",
             "file2.c",
             "file3.py",
             "file4.rb",
             "file5.py",
             "file6.docx",
             "file7.md"]

    expected_ratio = {
        CodingLanguage.C: (2/5),
        CodingLanguage.PYTHON: (2/5),
        CodingLanguage.RUBY: (1/5)
    }

    # We should see C language be 0.4, py be 0.4 and ruby be 0.2

    reports = []

    # Make files and log their reports
    for file in files:
        path = tmp_path / file
        Path(path).write_text("")

        reports.append(get_ready_specific_analyzer(
            str(tmp_path), file).analyze())

    project_report = ProjectReport(
        reports, calculator_classes=[CodingLanguageRatio])

    coding_language_ratio = project_report.get_value(
        ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

    assert len(coding_language_ratio) == len(expected_ratio)
    assert len(coding_language_ratio) == len(expected_ratio)
