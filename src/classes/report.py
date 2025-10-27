"""
Reports hold statistics.
"""
from typing import Any, Optional
from pathlib import Path
import tempfile
import shutil
import zipfile
from .statistic import Statistic, StatisticTemplate, StatisticIndex, ProjectStatCollection, FileStatCollection, UserStatCollection, WeightedSkills
from typing import Any
from datetime import datetime, date


class BaseReport:
    """
    This is the BaseReport class. A report is a class that holds
    statistics.
    """

    def __init__(self, statistics: StatisticIndex):
        self.statistics = statistics

    def add_statistic(self, stat: Statistic):
        self.statistics.add(stat)

    def get(self, template: StatisticTemplate):
        return self.statistics.get(template)

    def get_value(self, template: StatisticTemplate) -> Any:
        return self.statistics.get_value(template)

    def to_dict(self) -> dict[str, Any]:
        return self.statistics.to_dict()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.to_dict()}>"


class FileReport(BaseReport):
    """
    The FileReport class is the lowest level report. It is made
    by file-type specific, analyzers.
    """

    path_to_file: str

    def __init__(self, statistics: StatisticIndex, path_to_file: str):
        super().__init__(statistics)
        self.path_to_file = path_to_file

    def get_filename(self):
        raise ValueError("Unimplemented")


class ProjectReport(BaseReport):
    """
    The ProjectReport class utilizes many FileReports to
    create many Project Statistics about a single project.

    For example, maybe we sum up all the lines of written
    in a FileReport to create a project level statistics
    of "total lines written."
    """

    def __init__(self, file_reports: list[FileReport]):
        # Extract all creation dates from file reports, filtering out None values
        # This creates a list of datetime objects representing when each file was created
        date_created_list = [report.get_value(FileStatCollection.DATE_CREATED.value) for report in file_reports if report.get_value(FileStatCollection.DATE_CREATED.value) is not None]

        # Extract all modification dates from file reports, filtering out None values  
        # This creates a list of datetime objects representing when each file was last modified
        date_modified_list = [report.get_value(FileStatCollection.DATE_MODIFIED.value) for report in file_reports if report.get_value(FileStatCollection.DATE_MODIFIED.value) is not None]


        # Build list of project-level statistics
        # Only add statistics that were successfully calculated
        project_stats = []
        
        # Find the earliest date (project start)
        if date_created_list:
            start_date = min(date_created_list)             # Find the minimum (earliest) date from all creation dates
            project_start_stat = Statistic(ProjectStatCollection.PROJECT_START_DATE.value, start_date)
            project_stats.append(project_start_stat)        # Add start date statistic if we found any creation dates

        # Find the latest modified date (project end)
        if date_modified_list:
            end_date = max(date_modified_list)              # Find the maximum (latest) date from all modification dates
            project_end_stat = Statistic(ProjectStatCollection.PROJECT_END_DATE.value, end_date)
            project_stats.append(project_end_stat)          # Add end date statistic if we found any modification dates   
        
            
        # Create StatisticIndex with project-level statistic
        project_statistics = StatisticIndex(project_stats)
        
        # Initialize the base class with the project statistics
        super().__init__(project_statistics)


class UserReport(BaseReport):
    """
    This UserReport class hold Statistics about the user. It is made
    from many different ReportReports
    """

    def __init__(self, file_reports: list[ProjectReport]):

        # Here we would take all the file stats and turn them into user stats

        raise ValueError("Unimplemented")
        return super().__init__(None)
