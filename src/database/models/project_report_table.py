'''
This table will store generated project reports. It has a
one-to-many relationship with the `project_report` table,
and a bi-directional many-to-many relationship with the
`user_report` table.

Key Columns:
- `id`: The table's PK
'''
from typing import List

from sqlalchemy import String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.database.base import Base
from src.database.utils.init_columns import make_columns
from src.database.models.association_table import association_table

from src.core.statistic import ProjectStatCollection


@make_columns(ProjectStatCollection)
class ProjectReportTable(Base):
    '''
    Example rows:
    | id  | project_name    | project_start_date         | project_end_date           | other columns...   |
    | --- | --------------- | -------------------------- | -------------------------- | ------------------ |
    | 1   | "project-one"   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | other statistics...|
    | 2   | "project-two"   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | other statistics...|
    | 3   | "project-three" |2025-01-05 04:48:26.875495  | 2025-10-21 13:51:15.185489 | other statistics...|
    | ... | ...             | ...                        | ...                        | ...                |
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
    project_path = mapped_column(String)
