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

from sqlalchemy import ForeignKey, Table, Column
from src.infrastructure.database.base import Base

association_table = Table(
    "association_table",
    Base.metadata,
    Column("project_report_id", ForeignKey(
        "project_report.id"), primary_key=True),
    Column("user_report_id", ForeignKey(
        "user_report.id"), primary_key=True),
)
