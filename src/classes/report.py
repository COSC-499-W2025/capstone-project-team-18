"""
Reports hold statistics. They are created from either a generator or a analyzer class
"""
from typing import Any
from statistic import Statistic, StatisticTemplate, StatisticIndex


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
    This ProjectReport class holds Statstics about a project. It
    is generated from many different FileReports
    """

    def __init__(self, file_reports: list[FileReport]):

        # Here we would take all the file stats and turn them into project stats

        raise ValueError("Unimplemented")
        return super().__init__(None)


class UserReport(BaseReport):
    """
    This UserReport class hold Statstics about the user. It is made
    from many different ReportReports
    """

    def __init__(self, file_reports: list[ProjectReport]):

        # Here we would take all the file stats and turn them into user stats

        raise ValueError("Unimplemented")
        return super().__init__(None)
