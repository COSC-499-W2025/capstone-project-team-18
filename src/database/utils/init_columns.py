'''
This file has two functions which are used to read all of the
statistic collections (FileStatCollection, ProjectStatCollection,
UserStatCollection) and dynamically create columns in their
respective tables as a result.
'''

from datetime import date
import typing as t

from sqlalchemy import Integer, Boolean, Float, JSON, String, Date
from sqlalchemy.orm import mapped_column


from src.classes.statistic import (
    FileStatCollection,
    ProjectStatCollection,
    UserStatCollection,
    CodingLanguage
)

# [type[src.classes.statistic.FileStatCollection], type[src.classes.statistic.ProjectStatCollection], type[src.classes.statistic.UserStatCollection]]
StatCollectionType = t.Union[
    type[FileStatCollection],
    type[ProjectStatCollection],
    type[UserStatCollection]
]


def _sqlalchemy_type_for(expected_type: t.Any):
    """
    Map a `StatisticTemplate.expected_type` to a SQLAlchemy column type
    for a new column.

    Supported mappings:
    - int -> Integer
    - str -> String
    - datetime.date -> Date
    - float -> Float
    - list[str], list[WeightedSkills], dict, CodingLanguage, set -> JSON
    - bool -> Boolean
    - Fallback: JSON
    """

    type_map = {
        int: Integer,
        str: String,
        date: Date,
        float: Float,
        list[str]: JSON,
        bool: Boolean,
        dict: JSON,
        CodingLanguage: JSON,
        set: JSON,
    }

    # E.g. return FileStatCollection.expected_type or JSON if not in found
    return type_map.get(expected_type, JSON)


def make_columns(stat_collection: StatCollectionType):
    """
    Loop through a enum collection class (e.g. `ProjectStatCollection`), get each
    statistic's name & expected type (e.g. "PROJECT_END_DATE", `date`), and make
    a column in that collection's table if it doesn't already exist.

    Example:
      `make_columns(FileStatCollection, FileReportTable)`
    """
    def decorator(cls):
        for member in stat_collection:
            template = member.value  # StatisticTemplate
            col_name = template.name.lower()  # e.g., "LINES_IN_FILE" -> "lines_in_file"
            column_type = _sqlalchemy_type_for(template.expected_type)
            setattr(cls, col_name, mapped_column(column_type))
        return cls
    return decorator
