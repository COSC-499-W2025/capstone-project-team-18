'''
This file contains all functions that will be called when we
want to access data from the database. In SQL, this would be
queries like INSERT, UPDATE, etc.
'''

from src.classes.report import FileReport, ProjectReport, UserReport
from src.database.db import FileReportTable, ProjectReportTable, UserReportTable, __repr__
from enum import Enum


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

        # Short Explanation
        # ----------------------------------------------------------
        # Convert Enum values into primitive JSON-serializable forms
        # ----------------------------------------------------------

        # Long Explanation
        # ----------------------------------------------------------
        # Some values that are stored in statistic templates can't
        # be translated into JSON by SQLAlchemy for one reason or
        # another. E.g. CODING_LANGUAGE_RATIO's expected_type stores
        # a dict where the keys are CodingLangauge enums, and the
        # values are the ratio (float). SQLAlchemy requires primitive
        # types for JSON keys and can't automatically convert a
        # CodingLanguage enum to a primitive type. So, we check for
        # these enum and either convert them to a string (for
        # something like FileDomain), or we get the first value of
        # the CodingLanguage enum object (a string of the coding
        # language)
        # ----------------------------------------------------------

        if isinstance(value, Enum):
            value = value.value  # e.g., FileDomain enums have a simple string .value
        if isinstance(value, dict):
            if col_name == 'coding_language_ratio':
                value = {lang.value[0]: ratio for lang, ratio in value.items()}
            else:
                continue
        if isinstance(value, list):
            if col_name == 'weighted_skills':
                value = [s.to_dict() for s in value]
            else:
                continue

        # add the statistic to the row if column exists
        if hasattr(row, col_name):
            setattr(row, col_name, value)
    return row
