'''
The resume table will store the formatted text versions of project reports, so that when the user
modifies a resume, we have a way to keep that edit persistent. It has a bi-directional many-to-many
relationship with the `project_report` table. We use the `resume_proj_assoc` table to store FK
references to both the `resume` table *and* the `project_report` table to track which project
reports are used in which resumes.
'''
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.resume.resume import Resume

from src.database.utils.init_columns import make_columns
from src.database.models.resume_proj_assoc_table import resume_proj_assoc_table
from src.database.base import Base


@make_columns(Resume)
class ResumeTable(Base):
    __tablename__ = 'resume'

    id: Mapped[int] = mapped_column(primary_key=True)  # PK

    # Many-to-many backref to ProjectReportTable
    project_reports = relationship(
        "ProjectReportTable",
        secondary=resume_proj_assoc_table,
        back_populates="resumes",
        cascade="save-update, merge"
    )
