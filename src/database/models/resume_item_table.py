'''
The user_report table will store generated user reports, which are made using
one or more project reports. It has a bi-directional many-to-many relationship with the
`project_report` table. We use `proj_user_assoc` to store FK references to both the `user_report`
table *and* the `project_report` table to track which project reports are used to make which user
reports.

Key Columns:
- `id`: The table's PK
'''
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.resume.resume import Resume

from src.database.utils.init_columns import make_columns
from src.database.models.resume_proj_assoc_table import resume_proj_assoc_table
from src.database.models.project_report_table import ProjectReportTable
from src.database.base import Base


@make_columns(Resume)
class ResumeItemTable(Base):
    __tablename__ = 'resume_item'

    id: Mapped[int] = mapped_column(primary_key=True)  # PK

    # Define a FK and many-to-one relationship with ProjectReport.
    # This will allow us to easily find the related project that
    # is used to create a given resume item.
    project_id: Mapped[int] = mapped_column(ForeignKey("project_report.id"))
    project_report: Mapped["ProjectReportTable"] = relationship(
        back_populates="resume_items")
