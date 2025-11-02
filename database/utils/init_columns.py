'''
This has two functions which are used to read all of the
statistic collections (FileStatCollection, ProjectStatCollection,
UserStatCollection) and dyanmically create columns in their
respective tables as a result.
'''

from datetime import date
import typing as t

from sqlalchemy import Column, Integer, DateTime, Boolean, Float, JSON, String


from src.classes.statistic import (
    FileStatCollection,
    ProjectStatCollection,
    UserStatCollection,
)

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
    - date -> DateTime
    - float -> Float
    - list[str], list[WeightedSkills], dict -> JSON
    - bool -> Boolean
    - Fallback: JSON
    """

    type_map = {
        int: Integer,
        str: String,
        date: DateTime,
        float: Float,
        list[str]: JSON,
        bool: Boolean,
        dict: JSON,
    }

    # E.g. return FileStatCollection.expected_type or JSON if not in found
    return type_map.get(expected_type, JSON)


def make_columns(stat_collection: StatCollectionType, table_cls: type) -> None:
    """
    Loop through a enum collection class (e.g. `ProjectStatCollection`), get each
    statistic's name & expected type (e.g. "PROJECT_END_DATE", `date`), and make
    a column in that collection's table if it doesn't already exist.

    Example:
      `make_columns(FileStatCollection, FileReportTable)`
    """
    print(stat_collection)
    for member in stat_collection:
        template = member.value  # StatisticTemplate
        col_name = template.name.lower()  # e.g., "LINES_IN_FILE" -> "lines_in_file"
        sa_type = _sqlalchemy_type_for(template.expected_type)

        # _sqlalchemy_type_for may return either a type class (Integer) or an
        # instance (Integer()). This line instantiates the obj if it's a class
        # and keeps the obj if it's already instantiated. This ensures that
        # the column we are creating is always of a valid TypeEngine instance
        type_engine = sa_type() if isinstance(sa_type, type) else sa_type

        # Only create the column if the table doesn't have it yet
        if not hasattr(table_cls, col_name):
            setattr(table_cls, col_name, Column(t.cast(t.Any, type_engine)))

    # no return because columns are attached via `setattr`
