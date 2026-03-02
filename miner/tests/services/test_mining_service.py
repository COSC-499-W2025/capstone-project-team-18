from src.services.mining_service import _compute_project_statistics_deltas
from src.core.statistic import Statistic, ProjectStatCollection, CodingLanguage


def test_compute_project_statistics_deltas_numeric_and_nested(project_report_from_stats):
    previous = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.TOTAL_PROJECT_LINES.value, 150),
            Statistic(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value, 40.0),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {
                    CodingLanguage.PYTHON: 0.5,
                    CodingLanguage.JAVASCRIPT: 0.5,
                },
            ),
        ],
        project_name="Project1_2",
    )

    current = project_report_from_stats(
        [
            Statistic(ProjectStatCollection.TOTAL_PROJECT_LINES.value, 200),
            Statistic(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value, 60.0),
            Statistic(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
                {
                    CodingLanguage.PYTHON: 0.7,
                    CodingLanguage.JAVASCRIPT: 0.3,
                },
            ),
        ],
        project_name="Project1_3",
    )

    deltas = _compute_project_statistics_deltas(current, previous)

    assert deltas["TOTAL_PROJECT_LINES"] == 50.0
    assert deltas["USER_COMMIT_PERCENTAGE"] == 20.0
    assert round(deltas["CODING_LANGUAGE_RATIO.Python"], 2) == 0.20
    assert round(deltas["CODING_LANGUAGE_RATIO.JavaScript"], 2) == -0.20
