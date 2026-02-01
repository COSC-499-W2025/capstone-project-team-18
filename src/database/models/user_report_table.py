'''
The user_report table will store generated user reports, which are made using
one or more project reports. It has a bi-directional many-to-many relationship with the
`project_report` table. We use `proj_user_assoc` to store FK references to both the `user_report`
table *and* the `project_report` table to track which project reports are used to make which user
reports.

Key Columns:
- `id`: The table's PK
'''
from typing import List

from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship, mapped_column, Mapped

from src.core.statistic import UserStatCollection

from src.database.utils.init_columns import make_columns
from src.database.models.proj_user_assoc_table import proj_user_assoc_table
from src.database.base import Base


@make_columns(UserStatCollection)
class UserReportTable(Base):
    '''
    Example rows:
    | id  | user_start_date            | user_end_date              | user_skills                               | other columns...    |
    | --- | -------------------------- | -------------------------- | ----------------------------------------- | ------------------- |
    | 1   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | ["Python",  "unix"]                       | other statistics... |
    | 2   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | ["Python", "Typescript", "Node", "Flask"] | other statistics... |
    | ... | ...                        | ...                        | ...                                       | ...                 |
    '''
    __tablename__ = 'user_report'

    id = mapped_column(Integer, primary_key=True)

    # name given by user, or name of zipped folder (default)
    title = mapped_column(String)

    # Many-to-many backref to ProjectReportTable
    project_reports = relationship(
        "ProjectReportTable",
        secondary=proj_user_assoc_table,
        back_populates="user_reports",
        cascade="save-update, merge"
    )

    # 1..1 with portfolio table
    portfolios: Mapped[List["PortfolioTable"]] = relationship(  # pyright: ignore[reportUndefinedVariable]
        back_populates="user_report", cascade="all, delete-orphan")
