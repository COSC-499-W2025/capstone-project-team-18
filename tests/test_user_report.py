from src.classes.report import UserReport, ProjectReport, FileReport
from src.classes.statistic import (
    StatisticIndex, Statistic, StatisticTemplate,
    UserStatCollection, WeightedSkills, ProjectStatCollection,
    FileStatCollection,
    CodingLanguage
)
from datetime import date
from datetime import datetime
import unittest
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Pytest-style tests for existing functionality

def test_to_user_readable_string():
    lang_ratio = {CodingLanguage.PYTHON: 0.8528,
                  CodingLanguage.CSS: 0.1002, CodingLanguage.TYPESCRIPT: 0.0470}
    idx = StatisticIndex([
        Statistic(UserStatCollection.USER_START_DATE.value, date(2023, 9, 20)),
        Statistic(UserStatCollection.USER_END_DATE.value,
                  date(2025, 10, 20)),
        Statistic(UserStatCollection.USER_CODING_LANGUAGE_RATIO.value, lang_ratio),
    ])
    report = UserReport.from_statistics(idx)
    out = report.to_user_readable_string()
    print(out)
    assert "You started your first project on 9/20/2023!" in out
    assert "Your latest contribution was on 10/20/2025." in out
    assert "Your coding languages: Python (85%), CSS (10%), Typescript (4%)"
    # assert "Your skills include: " in out


def test_to_user_readable_string_empty():
    idx = StatisticIndex()
    report = UserReport.from_statistics(idx)
    assert report.to_user_readable_string() == "No user statistics are available yet."


def test_to_user_readable_string_fallback_generic_title_value():
    dummy_template = StatisticTemplate(
        name="CUSTOM_UNKNOWN_STAT",
        description="A stat not covered by custom phrasing",
        expected_type=int,
    )
    idx = StatisticIndex([Statistic(dummy_template, 42)])
    report = UserReport.from_statistics(idx)
    out = report.to_user_readable_string()
    assert "Custom Unknown Stat: 42" in out

 # Unittest-style tests for the new date functionality


class TestUserReportDates(unittest.TestCase):

    def test_user_dates_from_multiple_projects(self):
        """Test user dates calculation from multiple projects"""
        # Create project 1 (earliest start, middle end)
        project1_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2022, 6, 15))
        ])
        project1 = ProjectReport.from_statistics(project1_stats)

        # Create project 2 (middle start, latest end)
        project2_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 3, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 12, 31))
        ])
        project2 = ProjectReport.from_statistics(project2_stats)

        # Create project 3 (latest start, earliest end)
        project3_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2022, 3, 15))
        ])
        project3 = ProjectReport.from_statistics(project3_stats)

        # Create user report
        user = UserReport([project1, project2, project3], "UserReport1")

        # Test user start date (earliest project start)
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        self.assertEqual(user_start, datetime(2022, 1, 1))

        # Test user end date (latest project end)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)
        self.assertEqual(user_end, datetime(2023, 12, 31))

    def test_empty_project_list(self):
        """Test that empty project list doesn't crash"""
        user = UserReport([], "")

        # Should not have start or end dates
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        self.assertIsNone(user_start)
        self.assertIsNone(user_end)

    def test_single_project(self):
        """Test with only one project"""
        project_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 5, 10)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 8, 20))
        ])
        project = ProjectReport.from_statistics(project_stats)

        user = UserReport([project], "UserReport2")

        # Start and end should be the same project's dates
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        self.assertEqual(user_start, datetime(2023, 5, 10))
        self.assertEqual(user_end, datetime(2023, 8, 20))

    def test_projects_with_missing_dates(self):
        """Test projects that have None values for dates"""
        # Project with only start date
        project1_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 6, 1))
        ])
        project1 = ProjectReport.from_statistics(project1_stats)

        # Project with only end date
        project2_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 9, 30))
        ])
        project2 = ProjectReport.from_statistics(project2_stats)

        # Project with both dates
        project3_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 15)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 4, 30))
        ])
        project3 = ProjectReport.from_statistics(project3_stats)

        user = UserReport([project1, project2, project3], "UserReport3")

        # Should use earliest start date from available projects
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        self.assertEqual(user_start, datetime(2022, 6, 1))

        # Should use latest end date from available projects
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)
        self.assertEqual(user_end, datetime(2023, 9, 30))

    def test_projects_with_no_dates(self):
        """Test projects that have no date statistics at all"""
        project_stats = StatisticIndex([])  # No statistics
        project = ProjectReport.from_statistics(project_stats)

        user = UserReport([project], "UserReport4")

        # Should have no dates
        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        self.assertIsNone(user_start)
        self.assertIsNone(user_end)

    def test_wrong_date_assumptions(self):
        """Test that dates are calculated correctly with assertFalse"""
        project1_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2022, 6, 15))
        ])
        project1 = ProjectReport.from_statistics(project1_stats)

        project2_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 12, 31))
        ])
        project2 = ProjectReport.from_statistics(project2_stats)

        user = UserReport([project1, project2], "UserReport5")

        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        # Assert wrong assumptions are false
        self.assertFalse(user_start == datetime(
            2023, 1, 1))  # Wrong start date
        self.assertFalse(user_end == datetime(2022, 6, 15))   # Wrong end date
        self.assertFalse(user_start == user_end)              # Start != End
        # Start should be before end
        self.assertFalse(user_start > user_end)

    def test_multiple_projects_complex_dates(self):
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
            stats = StatisticIndex([
                Statistic(
                    ProjectStatCollection.PROJECT_START_DATE.value, start_date),
                Statistic(ProjectStatCollection.PROJECT_END_DATE.value, end_date)
            ])
            projects.append(ProjectReport.from_statistics(stats))

        user = UserReport(projects, "UserReport6")

        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        # Should be earliest start and latest end
        self.assertEqual(user_start, datetime(2021, 6, 1))
        self.assertEqual(user_end, datetime(2024, 1, 31))

        # Assert false conditions
        self.assertFalse(user_start == datetime(
            2021, 12, 1))  # Not the second earliest
        self.assertFalse(user_end == datetime(
            2023, 11, 30))   # Not the second latest

    def test_user_report_inheritance(self):
        """Test that UserReport properly inherits from BaseReport"""
        project_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2023, 1, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2023, 12, 31))
        ])
        project = ProjectReport.from_statistics(project_stats)

        user = UserReport([project], "UserReport7")

        # Test inherited methods work
        self.assertIsNotNone(user.to_dict())
        self.assertIsInstance(user.to_dict(), dict)

        # Test that repr doesn't crash
        repr_str = repr(user)
        self.assertIsInstance(repr_str, str)
        self.assertTrue("UserReport" in repr_str)

    def test_user_timeline_progression(self):
        """Test realistic user timeline progression"""
        # Simulate a user's career progression over time
        # Project 1: College project
        college_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2020, 9, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2020, 12, 15))
        ])
        college_project = ProjectReport.from_statistics(college_stats)

        # Project 2: Internship project
        internship_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2021, 6, 1)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2021, 8, 31))
        ])
        internship_project = ProjectReport.from_statistics(internship_stats)

        # Project 3: Full-time work project
        work_stats = StatisticIndex([
            Statistic(ProjectStatCollection.PROJECT_START_DATE.value,
                      datetime(2022, 1, 3)),
            Statistic(ProjectStatCollection.PROJECT_END_DATE.value,
                      datetime(2024, 10, 27))
        ])
        work_project = ProjectReport.from_statistics(work_stats)

        user = UserReport(
            [college_project, internship_project, work_project], "UserReport8")

        user_start = user.get_value(UserStatCollection.USER_START_DATE.value)
        user_end = user.get_value(UserStatCollection.USER_END_DATE.value)

        # User started in college, most recent work is current
        self.assertEqual(user_start, datetime(2020, 9, 1))
        self.assertEqual(user_end, datetime(2024, 10, 27))

        # Verify timeline makes sense
        self.assertTrue(user_start < user_end)
        self.assertEqual((user_end - user_start).days,
                         (datetime(2024, 10, 27) - datetime(2020, 9, 1)).days)


if __name__ == '__main__':
    # Run both pytest functions and unittest TestCase
    test_to_user_readable_string()
    test_to_user_readable_string_empty()
    test_to_user_readable_string_fallback_generic_title_value()
    # print("Pytest-style tests passed!")

    # Run unittest tests
    unittest.main()
