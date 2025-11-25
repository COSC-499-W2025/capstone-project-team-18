"""
Tests the Resume class and its methods.
"""

from src.classes.resume import Resume, ResumeItem
from src.classes.report import ProjectReport, UserReport
from src.classes.statistic import StatisticIndex, Statistic, ProjectStatCollection
from datetime import date


def test_add_item():
    resume = Resume()
    item = ResumeItem(
        title="Software Engineer",
        bullet_points=["Developed features", "Fixed bugs"],
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1)
    )
    resume.add_item(item)
    assert len(resume.items) == 1
    assert resume.items[0].title == "Software Engineer"


def test_add_skill():
    resume = Resume()
    resume.add_skill("Python")
    resume.add_skill("Java")
    assert len(resume.skills) == 2
    assert "Python" in resume.skills
    assert "Java" in resume.skills


def test_generate_resume():
    resume = Resume()
    item = ResumeItem(
        title="Software Engineer",
        bullet_points=["Developed features", "Fixed bugs"],
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1)
    )
    resume.add_item(item)
    generated = resume.generate_resume()
    expected_output = (
        "Software Engineer : 2020-01-01 - 2021-01-01\n"
        "   - Developed features\n"
        "   - Fixed bugs\n"
        "\n"
    )
    assert generated == expected_output


def test_projectreport_can_create_resume():

    statistics = StatisticIndex()
    report = ProjectReport.from_statistics(statistics)
    resume_item = report.generate_resume_item()
    assert isinstance(resume_item, ResumeItem)

    assert resume_item.title == "TESTING ONLY SHOULD SEE THIS IN PYTEST"


def test_userreport_can_create_resume():
    from src.classes.report import UserReport
    from src.classes.statistic import StatisticIndex

    project_statistics = StatisticIndex([
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  date(2020, 1, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value, date(2021, 1, 1))
    ])

    user_report = UserReport(
        [ProjectReport.from_statistics(project_statistics)]
    )

    resume_item = user_report.generate_resume()

    assert isinstance(resume_item, Resume)
    assert len(resume_item.items) == 1
    assert resume_item.items[0].title == "TESTING ONLY SHOULD SEE THIS IN PYTEST"
    assert resume_item.items[0].start_date == date(2020, 1, 1)
    assert resume_item.items[0].end_date == date(2021, 1, 1)
