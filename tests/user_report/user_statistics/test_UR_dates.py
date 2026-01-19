"""
Test the User Level statistic of USER_START_DATE and USER_END_DATE.
"""

from src.core.report import UserReport
from src.core.statistic import (
    Statistic, UserStatCollection, ProjectStatCollection
)
from datetime import datetime


def test_user_dates_from_multiple_projects(project_report_from_stats):
    """Test user dates calculation from multiple projects"""
    # Create project 1 (earliest start, middle end)
    project1_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2022, 1, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2022, 6, 15))
    ]

    project1 = project_report_from_stats(project1_stats)

    # Create project 2 (middle start, latest end)
    project2_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2022, 3, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2023, 12, 31))
    ]
    project2 = project_report_from_stats(project2_stats)

    # Create project 3 (latest start, earliest end)
    project3_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2023, 1, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2022, 3, 15))
    ]

    project3 = project_report_from_stats(project3_stats)

    user = UserReport([project1, project2, project3], "UserReport1")

    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

    assert user_start == datetime(2022, 1, 1)
    assert user_end == datetime(2023, 12, 31)


def test_empty_project_list():
    """Test that empty project list doesn't crash"""
    user = UserReport([], "")

    # Should not have start or end dates
    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

    assert user_start is None
    assert user_end is None


def test_single_project(project_report_from_stats):
    """Test with only one project"""
    project_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2023, 5, 10)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2023, 8, 20))
    ]
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "UserReport2")

    # Start and end should be the same project's dates
    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

    assert user_start == datetime(2023, 5, 10)
    assert user_end == datetime(2023, 8, 20)


def test_projects_with_missing_dates(project_report_from_stats):
    """Test projects that have None values for dates"""
    # Project with only start date
    project1_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2022, 6, 1))
    ]
    project1 = project_report_from_stats(project1_stats)

    # Project with only end date
    project2_stats = [
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2023, 9, 30))
    ]
    project2 = project_report_from_stats(project2_stats)

    # Project with both dates
    project3_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2023, 1, 15)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2023, 4, 30))
    ]
    project3 = project_report_from_stats(project3_stats)

    user = UserReport([project1, project2, project3], "UserReport3")

    # Should use earliest start date from available projects
    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    assert user_start == datetime(2022, 6, 1)

    # Should use latest end date from available projects
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)
    assert user_end == datetime(2023, 9, 30)


def test_projects_with_no_dates(project_report_from_stats):
    """Test projects that have no date statistics at all"""
    project_stats = []  # No statistics
    project = project_report_from_stats(project_stats)

    user = UserReport([project], "UserReport4")

    # Should have no dates
    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

    assert user_start is None
    assert user_end is None


def test_wrong_date_assumptions(project_report_from_stats):
    """Test that dates are calculated correctly with assertFalse"""
    project1_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2022, 1, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2022, 6, 15))
    ]
    project1 = project_report_from_stats(project1_stats)

    project2_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2023, 1, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2023, 12, 31))
    ]
    project2 = project_report_from_stats(project2_stats)

    user = UserReport([project1, project2], "UserReport5")

    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

    # Assert wrong assumptions are false
    assert not (user_start == datetime(2023, 1, 1))  # Wrong start date
    assert not (user_end == datetime(2022, 6, 15))   # Wrong end date
    assert not (user_start == user_end)              # Start != End
    # Start should be before end
    assert not (user_start > user_end)


def test_multiple_projects_complex_dates(project_report_from_stats):
    """Test with many projects and complex date patterns"""
    projects = []

    # Create 5 projects with various dates
    project_dates = [
        (datetime(2021, 6, 1), datetime(2021, 8, 30)),   # Earliest start
        (datetime(2022, 1, 15), datetime(2022, 12, 20)),
        (datetime(2022, 6, 1), datetime(2024, 1, 31)),   # Latest end
        (datetime(2021, 12, 1), datetime(2022, 3, 15)),
        (datetime(2023, 3, 1), datetime(2023, 11, 30))
    ]

    for i, (start_date, end_date) in enumerate(project_dates):
        stats = [
            Statistic(
                ProjectStatCollection.PROJECT_START_DATE.value, start_date),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value, end_date)
        ]
        projects.append(project_report_from_stats(stats))

    user = UserReport(projects, "UserReport6")

    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

    # Should be earliest start and latest end
    assert user_start == datetime(2021, 6, 1)
    assert user_end == datetime(2024, 1, 31)

    # Assert false conditions
    assert not (user_start == datetime(2021, 12, 1))  # Not the second earliest
    assert not (user_end == datetime(2023, 11, 30))   # Not the second latest


def test_user_timeline_progression(project_report_from_stats):
    """Test realistic user timeline progression"""
    # Simulate a user's career progression over time
    # Project 1: College project
    college_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2020, 9, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2020, 12, 15))
    ]
    college_project = project_report_from_stats(college_stats)

    # Project 2: Internship project
    internship_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2021, 6, 1)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2021, 8, 31))
    ]
    internship_project = project_report_from_stats(internship_stats)

    # Project 3: Full-time work project
    work_stats = [
        Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                  datetime(2022, 1, 3)),
        Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                  datetime(2024, 10, 27))
    ]
    work_project = project_report_from_stats(work_stats)

    user = UserReport(
        [college_project, internship_project, work_project], "UserReport8")

    user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
    user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

    # User started in college, most recent work is current
    assert user_start == datetime(2020, 9, 1)
    assert user_end == datetime(2024, 10, 27)

    # Verify timeline makes sense
    assert user_start < user_end
    assert (user_end - user_start).days == (datetime(2024,
                                                     10, 27) - datetime(2020, 9, 1)).days
