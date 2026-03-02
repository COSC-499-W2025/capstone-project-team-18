"""
Tests the Resume class and its methods.
"""

from src.core.resume.resume import Resume, ResumeItem
from src.core.statistic import Statistic, ProjectStatCollection
from datetime import date
from src.core.report import UserReport
from datetime import datetime


def test_add_item():
    resume = Resume()
    item = ResumeItem(
        title="Software Engineer",
        frameworks=[],
        bullet_points=["Developed features", "Fixed bugs"],
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1)
    )
    resume.add_item(item)
    assert len(resume.items) == 1
    assert resume.items[0].title == "Software Engineer"


def test_generate_resume():
    resume = Resume()
    item = ResumeItem(
        title="Software Engineer",
        frameworks=[],
        bullet_points=["Developed features", "Fixed bugs"],
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1)
    )
    resume.add_item(item)
    generated = str(resume)
    expected_output = (
        "Software Engineer : January, 2020 - January, 2021\n"
        "   - Developed features\n"
        "   - Fixed bugs\n"
        "\n"
    )
    assert generated == expected_output


def test_projectreport_can_create_resume(project_report_from_stats):

    statistics = []
    report = project_report_from_stats(statistics)
    resume_item = report.generate_resume_item()
    assert isinstance(resume_item, ResumeItem)

    assert resume_item.title == "TESTING ONLY SHOULD SEE THIS IN PYTEST"


def test_userreport_can_create_resume(project_report_from_stats):

    project_statistics = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2020, 1, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2021, 1, 1))
    ]

    user_report = UserReport(
        [project_report_from_stats(project_statistics)],
        "UserReport1"
    )

    resume_item = user_report.generate_resume(None, None)

    assert isinstance(resume_item, Resume)
    assert len(resume_item.items) == 1
    assert resume_item.items[0].title == "TESTING ONLY SHOULD SEE THIS IN PYTEST"
    assert resume_item.items[0].start_date == datetime(2020, 1, 1)
    assert resume_item.items[0].end_date == datetime(2021, 1, 1)


def test_userreport_adds_since_last_analysis_item(project_report_from_stats):
    project_statistics = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2020, 1, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2021, 1, 1)),
        Statistic(ProjectStatCollection.PREVIOUS_ANALYSIS_PROJECT.value,
                  "Project1_2"),
        Statistic(ProjectStatCollection.PROJECT_STATISTICS_DELTA.value,
                  {
                      "TOTAL_PROJECT_LINES": 120.0,
                      "USER_COMMIT_PERCENTAGE": 10.0,
                  }),
    ]

    user_report = UserReport(
        [project_report_from_stats(project_statistics, project_name="Project1_3")],
        "UserReport1"
    )

    resume = user_report.generate_resume(None, None)

    assert len(resume.items) == 2
    assert resume.items[1].title == "Project1 metrics since last analysis"
    assert any(
        "TOTAL_PROJECT_LINES increased by 120.00" in bullet
        for bullet in resume.items[1].bullet_points
    )
