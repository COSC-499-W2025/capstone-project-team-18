from src.classes.report import ProjectReport, FileReport
from src.classes.statistic import (
    StatisticIndex,
    Statistic,
    FileStatCollection,
    ProjectStatCollection,
)


def test_project_tags_from_readme_keyphrases():
    stats = StatisticIndex([
        Statistic(FileStatCollection.README_KEYPHRASES.value,
                  ["REST API", "OAuth", "PostgreSQL"]),
    ])
    file_report = FileReport(stats, filepath="README.md")

    report = ProjectReport(file_reports=[file_report],
                           project_name="ProjectTagsTest")

    tags = report.get_value(ProjectStatCollection.PROJECT_TAGS.value)
    assert tags == ["REST API", "OAuth", "PostgreSQL"]
