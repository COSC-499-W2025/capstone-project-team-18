'''
This file will store all of the config and logic that we will need to access and modify our database (`db.py`)
'''
from sqlalchemy import ForeignKey, Table, Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column, Session
from enum import Enum
from dataclasses import is_dataclass, asdict
from typing import List

from src.classes.statistic import FileStatCollection, ProjectStatCollection, UserStatCollection, StatisticIndex, Statistic
from .utils.init_columns import make_columns

DB_PATH = "sqlite:///src/database/data.db"


class Base(DeclarativeBase):
    pass


'''
Since project_report and user_report have a bi-directional relationship,
we need an association table to track which project reports are used to
create which user reports, and vice versa.

Example Rows:
| project_report_id | user_report_id |
| ----------------- | -------------- |
| 1                 | 1              |
| 2                 | 2              |
| 3                 | 1              |
| ...               | ...            |
'''
association_table = Table(
    "association_table",
    Base.metadata,
    Column("project_report_id", ForeignKey(
        "project_report.id"), primary_key=True),
    Column("user_report_id", ForeignKey(
        "user_report.id"), primary_key=True),
)


@make_columns(FileStatCollection)
class FileReportTable(Base):
    '''
    This table will store generated file reports. It has a
    many-to-one relationship with the `project_report` table.

    Example rows:
    | id  | project_id | filepath                                          | lines_in_code | date_created               | date_modified              | other columns...   |
    | --- | ---------- | ------------------------------------------------- | ------------- | -------------------------- | -------------------------- | ------------------ |
    | 1   | 1          | /tmp/proj_one/app.py                              | 265           | 2024-11-15 09:45:15.218714 | 2025-03-25 11:53:12.237414 | other statistics...|
    | 2   | 2          | /tmp/proj_two/src/app/page.tsx                    | 189           | 2024-10-28 10:03:59.187515 | 2024-12-14 15:35:54.564158 | other statistics...|
    | 3   | 2          | /tmp/proj_two/src/apps/components/navbar/page.tsx | 122           | 2025-03-26 15:13:29.549154 | 2025-07-12 19:43:22.186141 | other statistics...|
    | 4   | 3          | /tmp/proj_three/clock.py                          | 241           | 2025-01-05 04:48:26.875495 | 2025-10-21 13:51:15.185489 | other statistics...|
    | ... | ...        | ...                                               | ...           | ...                        | ...                        | ...                |

    Key Columns:
    - `id`: The table's PK
    - `project_id`: A FK reference to `project_report`'s PK. It has a many-to-one relationship.
    '''
    __tablename__ = 'file_report'

    id: Mapped[int] = mapped_column(primary_key=True)  # PK

    # Define a FK and many-to-one relationship with ProjectReport.
    # This will allow us to easily find the related file reports that are used to create
    # a given project report
    project_id: Mapped[int] = mapped_column(ForeignKey("project_report.id"))
    project_report: Mapped["ProjectReportTable"] = relationship(
        back_populates="file_reports")

    # path to the file when we unzip to the temp dir
    filepath = mapped_column(String)


@make_columns(ProjectStatCollection)
class ProjectReportTable(Base):
    '''
    This table will store generated project reports. It has a
    one-to-many relationship with the `project_report` table,
    and a bi-directional many-to-many relationship with the
    `user_report` table.

    Example rows:
    | id  | project_name    | project_start_date         | project_end_date           | other columns...   |
    | --- | --------------- | -------------------------- | -------------------------- | ------------------ |
    | 1   | "project-one"   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | other statistics...|
    | 2   | "project-two"   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | other statistics...|
    | 3   | "project-three" |2025-01-05 04:48:26.875495  | 2025-10-21 13:51:15.185489 | other statistics...|
    | ... | ...             | ...                        | ...                        | ...                |

    Key Columns:
    - `id`: The table's PK
    '''
    __tablename__ = 'project_report'

    id: Mapped[int] = mapped_column(primary_key=True)  # PK

    file_reports: Mapped[List["FileReportTable"]] = relationship(
        back_populates="project_report",
        # see https://docs.sqlalchemy.org/en/20/orm/cascades.html#cascades
        cascade="all, delete-orphan",
    )

    # Many-to-many with UserReport via association table
    user_reports = relationship(
        "UserReportTable",
        secondary=association_table,
        back_populates="project_reports",
        cascade="save-update, merge"
    )

    project_name = mapped_column(String)


@make_columns(UserStatCollection)
class UserReportTable(Base):
    '''
    This table is **INCOMPLETE**. The table will store generated user reports, which are made using
    one or more project reports. It has a bi-directional many-to-many relationship with the
    `project_report` table. We use `association_table` to store FK references to both the `user_report`
    table *and* the `project_report` table to track which project reports are used to make which user
    reports.

    Example rows:
    | id  | user_start_date            | user_end_date              | user_skills                               | other columns...    |
    | --- | -------------------------- | -------------------------- | ----------------------------------------- | ------------------- |
    | 1   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | ["Python",  "unix"]                       | other statistics... |
    | 2   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | ["Python", "Typescript", "Node", "Flask"] | other statistics... |
    | ... | ...                        | ...                        | ...                                       | ...                 |

    Key Columns:
    - `id`: The table's PK
    '''
    __tablename__ = 'user_report'

    id = mapped_column(Integer, primary_key=True)

    # name given by user, or name of zipped folder (default)
    title = mapped_column(String)

    # Many-to-many backref to ProjectReportTable
    project_reports = relationship(
        "ProjectReportTable",
        secondary=association_table,
        back_populates="user_reports",
        cascade="save-update, merge"
    )


def __repr__(table: FileReportTable | ProjectReportTable | UserReportTable):
    '''
    Prints the rows of a given table in a dict-like format.
    '''
    cols = table.__table__.columns.keys()
    d = {c: getattr(table, c) for c in cols}
    return str(d)


def get_engine():
    '''
    The engine acts as a central sources of all connections to the DB.
    It is a factory & also manages a connection pool for the connections
    '''
    return create_engine(DB_PATH, future=True)


if __name__ == "__main__":
    '''
    Run `python -m src.database.db`
    to initialize the database.
    '''
    eng = get_engine()
    Base.metadata.create_all(eng)
