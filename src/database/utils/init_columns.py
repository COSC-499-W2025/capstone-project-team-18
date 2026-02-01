'''
This file has two functions which are used to read all of the
statistic collections (FileStatCollection, ProjectStatCollection,
UserStatCollection) and dynamically create columns in their
respective tables as a result.
'''

from src.database.utils.column_statistic_serializer import ColumnStatisticSerializer
from src.core.resume.resume import Resume
from src.core.statistic import (
    FileStatCollection,
    ProjectStatCollection,
    UserStatCollection
)
from datetime import date
import typing as t
from enum import Enum

from sqlalchemy import Integer, Boolean, Float, String, Date
from sqlalchemy.orm import mapped_column

from src.infrastructure.log.logging import get_logger
logger = get_logger(__name__)


# [type[src.core.statistic.FileStatCollection], type[src.core.statistic.ProjectStatCollection], type[src.core.statistic.UserStatCollection]]
CollectionType = t.Union[
    type[FileStatCollection],
    type[ProjectStatCollection],
    type[UserStatCollection],
    type[Resume]
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
    - bool -> Boolean

    - Fallback: ColumnStatisticSerializer
    """

    type_map = {
        int: Integer,
        str: String,
        date: Date,
        float: Float,
        bool: Boolean,
    }

    # E.g. return FileStatCollection.expected_type or ColumnStatisticSerializer if not in found
    return type_map.get(expected_type, ColumnStatisticSerializer)


<< << << < HEAD


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


== == == =


def make_columns(collection: CollectionType):
    """
    Dynamically creates the columns for our tables.

    For the statistic collections (e.g. `ProjectStatCollection`):
    - Loop through the stat enum, get each statistic's name &
    expected type (e.g. "PROJECT_END_DATE", `date`), and make a
    column in that collection's table if it doesn't already exist.
    - Example: `make_columns(FileStatCollection, FileReportTable)`

    For objects (e.g., the `Resume` class):
    - Loop through the object's attributes (e.g., `items[]`,
    `email`), get the attribute's name and type, and make a column
    in the object's table if it doesn't already exist.
    """

    def decorator(cls):
        if issubclass(collection, Enum):
            logger.info(f'COLUMNS FOR TABLE: {collection}')
            for member in collection:
                template = member.value  # StatisticTemplate
                col_name = template.name.lower()  # e.g., "LINES_IN_FILE" -> "lines_in_file"
                col_type = _sqlalchemy_type_for(template.expected_type)
                logger.info(f'Column Name: {col_name}, Type: {col_type}')
                setattr(cls, col_name, mapped_column(col_type))
        else:
            for attr_name in dir(collection):
                # filter out built-in attrs like __name__
                if not attr_name.startswith('__'):
                    col_name = attr_name
                    col_type = type(getattr(collection, attr_name))
                    setattr(cls, col_name, col_type)


>>>>>> > milestone-two-db-config
        return cls
    return decorator
