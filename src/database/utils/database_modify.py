'''
This file contains all functions that will be called when we
want to access data from the database. In SQL, this would be
queries like INSERT, UPDATE, etc.
'''

from src.classes.report import FileReport, ProjectReport, UserReport
from src.database.db import FileReportTable, ProjectReportTable, UserReportTable, __repr__


def create_row(report: FileReport | ProjectReport | UserReport):
    '''
    Returns a new row for a given type of report object.
    - Equivalent to an SQL `INSERT` statement.

    Example: a new row for the `file_report`
    table (i.e., a new `FileReportTable` object) is
    returned) if a `FileReport` object is passed in.
    '''
    if isinstance(report, FileReport):
        row = FileReportTable()
        row.filepath = report.filepath
    elif isinstance(report, ProjectReport):
        row = ProjectReportTable()
        if report.project_name:
            row.project_name = report.project_name
    elif isinstance(report, UserReport):
        row = UserReportTable()
    else:
        raise ValueError(f"Unknown report type: {type(report)}")

    # `report.statistics` is a StatisticIndex and is iterable over Statistic
    for stat in report.statistics:
        if stat is None:
            continue  # column will be NULL if there is no statistic

        col_name = stat.get_template().name.lower()
        value = stat.value

        # add the statistic to the row
        if hasattr(row, col_name):
            setattr(row, col_name, value)
    return row
