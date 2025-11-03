'''
This file will store all of the config and logic that we will need to access and modify our database (`db.py`)
'''
from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy import Table
from sqlalchemy import Column, Integer, DateTime, Boolean, Float, JSON, String, Date
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

from src.classes.statistic import FileStatCollection, ProjectStatCollection, UserStatCollection, WeightedSkills
from .utils.init_columns import make_columns

DB_PATH = "sqlite:///database/data.db"


class Base(DeclarativeBase):
    pass


class UserPreferencesTable(Base):
    '''
    This table will only contain 1 row.
    Its logic needs to be fixed to ensure this
    '''
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    consent = Column(Boolean)

    # E.g. files_to_ignore=['tmp.log', 'README.md']
    files_to_ignore = Column(JSON)

    # Ignore all files that are younger or older than these values
    file_start_time = Column(DateTime)
    file_end_time = Column(DateTime)
    # TODO: Implement other user preferences.


'''
Since project_report and user_report have a bi-directional relationship,
we need an association table to track which project reports are used to
create which user reports, and vice versa.

Example Rows:
| project_report_id | user_report_id |
| ----------------- | -------------- |
| 1                 | 1              |
| 3                 | 1              |
| 2                 | 2              |
'''
association_table = Table(
    "association_table",
    Base.metadata,
    Column("project_report_id", ForeignKey(
        "project_report.id"), primary_key=True),
    Column("user_report_id", ForeignKey("user_report.id"), primary_key=True),
)


class FileReportTable(Base):
    '''
    This table will store generated file reports. It has a
    many-to-one relationship with the `project_report` table.

    Example rows:
    | id  | project_id | date_created               | date_modified              | other columns...    |
    | --- | ---------- | -------------------------- | -------------------------- | ------------------- |
    | 23  | 2          | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | other statistics... |
    | 24  | 2          | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | other statistics... |
    | 24  | 3          | 2025-03-26 15:13:29.549154 | 2025-07-12 19:43:22.186141 | other statistics... |

    Key Columns:
    - `id`: The table's PK
    - `project_id`: A FK reference to `project_report`'s PK. It has a many-to-one relationship.
    '''
    __tablename__ = 'file_report'

    id = Column(Integer, primary_key=True)  # PK

    # Define a FK and one-to-many relationship with ProjectReport.
    # This will allow us to easily find the related file reports that are used to create
    # a given project report
    project_id = Column(Integer, ForeignKey("project_report.id"))
    project_report = relationship(
        "ProjectReportTable", back_populates="file_reports")

    filepath = Column(String)  # path to the file when we unzip to the temp dir


class ProjectReportTable(Base):
    '''
    This table will store generated project reports. It has a
    one-to-many relationship with the `project_report` table,
    and a bi-directional many-to-many relationship with the
    `user_report` table.

    Example rows:
    | id  | is_group_project | project_start_date         | project_end_date           | other columns...   |
    | --- | ---------------- | -------------------------- | -------------------------- | ------------------ |
    | 1   | True             | 2024-11-15 09:45:15.218714 | 2025-03-25 11:53:12.237414 | other statistics...|
    | 2   | True             | 2024-10-28 14:23:59.187515 | 2024-12-14 15:35:54.56415  | other statistics...|
    | 3   | False            | 2025-02-18 10:45:23.358411 | 2025-04-23 15:51:46.184716 | other statistics...|

    Key Columns:
    - `id`: The table's PK
    '''
    __tablename__ = 'project_report'

    id = Column(Integer, primary_key=True)  # PK

    # Establish one-to-many relationship with FileReport
    file_reports = relationship(
        "FileReportTable", back_populates="project_report")

    # Many-to-many with UserReport via association table
    user_reports = relationship(
        "UserReportTable",
        secondary=association_table,
        back_populates="project_reports",
    )


class UserReportTable(Base):
    '''
    This table is **INCOMPLETE**. The table will store generated user reports, which are made using
    one or more project reports. It has a bi-directional many-to-many relationship with the
    `project_report` table. We use `association_table` to store FK references to both the `user_report`
    table *and* the `project_report` table to track which project reports are used to make which user
    reports.

    Key Columns:
    - `id`: The table's PK
    '''
    __tablename__ = 'user_report'

    id = Column(Integer, primary_key=True)
    # Many-to-many backref to ProjectReportTable
    project_reports = relationship(
        "ProjectReportTable",
        secondary=association_table,
        back_populates="user_reports",
    )


def get_engine(db_path: str):
    '''
    The engine acts as a central sources of all connections to the DB.
    It is a factory & also manages a connection pool for the connections
    '''
    return create_engine(db_path, echo=True, future=True)


def init_db(engine):
    '''
    Create tables with their columns
    '''
    # Dynamically attach Statistic columns after classes are defined
    make_columns(FileStatCollection, FileReportTable)
    make_columns(ProjectStatCollection, ProjectReportTable)
    make_columns(UserStatCollection, UserReportTable)

    Base.metadata.create_all(engine)
