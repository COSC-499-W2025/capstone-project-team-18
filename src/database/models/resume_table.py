'''
The user_report table will store generated user reports, which are made using
one or more project reports. It has a bi-directional many-to-many relationship with the
`project_report` table. We use `proj_user_assoc` to store FK references to both the `user_report`
table *and* the `project_report` table to track which project reports are used to make which user
reports.

Key Columns:
- `id`: The table's PK
'''
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.resume.resume import Resume

from src.database.utils.init_columns import make_columns
from src.database.models.resume_proj_assoc_table import resume_proj_assoc_table
from src.database.base import Base


@make_columns(Resume)
class ResumeTable(Base):
    '''
    Example rows:
    | id  | user_start_date            | user_end_date              | user_skills                               | other columns...    |
    | --- | -------------------------- | -------------------------- | ----------------------------------------- | ------------------- |
    | 1   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | ["Python",  "unix"]                       | other statistics... |
    | 2   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | ["Python", "Typescript", "Node", "Flask"] | other statistics... |
    | ... | ...                        | ...                        | ...                                       | ...                 |
    '''
    __tablename__ = 'resume'

    id: Mapped[int] = mapped_column(primary_key=True)  # PK

    # Many-to-many backref to ProjectReportTable
    project_reports = relationship(
        "ProjectReportTable",
        secondary=resume_proj_assoc_table,
        back_populates="resumes",
        cascade="save-update, merge"
    )
