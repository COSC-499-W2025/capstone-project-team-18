import unittest
import sys
import os
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classes.report import ProjectReport, FileReport
from src.classes.statistic import StatisticIndex, Statistic, FileStatCollection, ProjectStatCollection

class TestProjectReport(unittest.TestCase):
    def test_project_dates(self):
        # Create mock file reports with different dates
        file1_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 1, 1)),
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 1, 15))
        ])
        file1 = FileReport(file1_stats, "file1.py")
        
        file2_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 2, 1)), 
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 2, 20))
        ])
        file2 = FileReport(file2_stats, "file2.py")
        
        # Create project report
        project = ProjectReport([file1, file2])
        
        # Test project start date (earliest created)
        start_date = project.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        self.assertEqual(start_date, datetime(2023, 1, 1))
        
        # Test project end date (latest modified) 
        end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        self.assertEqual(end_date, datetime(2023, 2, 20))

    def test_empty_file_reports_list(self):
        """Test that empty file reports list doesn't crash"""
        project = ProjectReport([])
        
        # Should not have start or end dates
        start_date = project.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        
        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

    def test_single_file_report(self):
        """Test with only one file report"""
        file_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 5, 10)),
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 5, 15))
        ])
        file_report = FileReport(file_stats, "single_file.py")
        
        project = ProjectReport([file_report])
        
        # Start and end should be the same file's dates
        start_date = project.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        
        self.assertEqual(start_date, datetime(2023, 5, 10))
        self.assertEqual(end_date, datetime(2023, 5, 15))

    def test_files_with_missing_dates(self):
        """Test files that have None values for dates"""
        # File with only creation date
        file1_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 3, 1))
        ])
        file1 = FileReport(file1_stats, "file1.py")
        
        # File with only modification date
        file2_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 3, 20))
        ])
        file2 = FileReport(file2_stats, "file2.py")
        
        # File with both dates
        file3_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 3, 5)),
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 3, 15))
        ])
        file3 = FileReport(file3_stats, "file3.py")
        
        project = ProjectReport([file1, file2, file3])
        
        # Should use earliest creation date from available files
        start_date = project.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        self.assertEqual(start_date, datetime(2023, 3, 1))
        
        # Should use latest modification date from available files
        end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        self.assertEqual(end_date, datetime(2023, 3, 20))

    def test_files_with_no_dates(self):
        """Test files that have no date statistics at all"""
        file_stats = StatisticIndex([])  # No statistics
        file_report = FileReport(file_stats, "no_dates.py")
        
        project = ProjectReport([file_report])
        
        # Should have no dates
        start_date = project.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        
        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

    def test_wrong_date_assumptions(self):
        """Test that dates are calculated correctly with assertFalse"""
        file1_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 1, 1)),
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 1, 15))
        ])
        file1 = FileReport(file1_stats, "file1.py")
        
        file2_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 2, 1)), 
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 2, 20))
        ])
        file2 = FileReport(file2_stats, "file2.py")
        
        project = ProjectReport([file1, file2])
        
        start_date = project.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        
        # Assert wrong assumptions are false
        self.assertFalse(start_date == datetime(2023, 2, 1))  # Wrong start date
        self.assertFalse(end_date == datetime(2023, 1, 15))   # Wrong end date
        self.assertFalse(start_date == end_date)              # Start != End
        self.assertFalse(start_date > end_date)               # Start should be before end

    def test_multiple_files_complex_dates(self):
        """Test with many files and complex date patterns"""
        files = []
        
        # Create 5 files with various dates
        dates = [
            (datetime(2023, 1, 5), datetime(2023, 1, 10)),   # Earliest creation
            (datetime(2023, 3, 1), datetime(2023, 3, 25)),   
            (datetime(2023, 2, 15), datetime(2023, 4, 30)),  # Latest modification
            (datetime(2023, 1, 20), datetime(2023, 2, 5)),
            (datetime(2023, 2, 1), datetime(2023, 3, 15))
        ]
        
        for i, (created, modified) in enumerate(dates):
            stats = StatisticIndex([
                Statistic(FileStatCollection.DATE_CREATED.value, created),
                Statistic(FileStatCollection.DATE_MODIFIED.value, modified)
            ])
            files.append(FileReport(stats, f"file{i}.py"))
        
        project = ProjectReport(files)
        
        start_date = project.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = project.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        
        # Should be earliest creation and latest modification
        self.assertEqual(start_date, datetime(2023, 1, 5))
        self.assertEqual(end_date, datetime(2023, 4, 30))
        
        # Assert false conditions
        self.assertFalse(start_date == datetime(2023, 1, 20))  # Not the second earliest
        self.assertFalse(end_date == datetime(2023, 3, 25))    # Not the second latest

    def test_project_report_inheritance(self):
        """Test that ProjectReport properly inherits from BaseReport"""
        file_stats = StatisticIndex([
            Statistic(FileStatCollection.DATE_CREATED.value, datetime(2023, 1, 1)),
            Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2023, 1, 15))
        ])
        file_report = FileReport(file_stats, "test.py")
        
        project = ProjectReport([file_report])
        
        # Test inherited methods work
        self.assertIsNotNone(project.to_dict())
        self.assertIsInstance(project.to_dict(), dict)
        
        # Test that repr doesn't crash
        repr_str = repr(project)
        self.assertIsInstance(repr_str, str)
        self.assertTrue("ProjectReport" in repr_str)

if __name__ == '__main__':
    unittest.main()