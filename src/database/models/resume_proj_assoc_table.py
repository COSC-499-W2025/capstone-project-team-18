'''
The resume and project_report tables have a bi-directional relationship,
so we use this association table to track which project reports are used to
create which resumes, and vice versa.

Example Rows:
| project_report_id | resume         |
| ----------------- | -------------- |
| 1                 | 1              |
| 2                 | 2              |
| 3                 | 1              |
| ...               | ...            |
'''

from sqlalchemy import ForeignKey, Table, Column
from src.database.base import Base

resume_proj_assoc_table = Table(
    "resume_proj_assoc",
    Base.metadata,
    Column("project_report_id", ForeignKey(
        "project_report.id"), primary_key=True),
    Column("resume_id", ForeignKey(
        "resume.id"), primary_key=True),
)
