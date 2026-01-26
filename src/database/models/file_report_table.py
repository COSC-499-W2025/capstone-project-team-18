'''
This table will store generated file reports. It has a
many-to-one relationship with the `project_report` table.

Key Columns:
- `id`: The table's PK
- `project_id`: A FK reference to `project_report`'s PK. It has a many-to-one relationship.
'''

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.statistic import FileStatCollection

from src.database.utils.init_columns import make_columns
from src.database.models.project_report_table import ProjectReportTable
from src.database.base import Base


@make_columns(FileStatCollection)
class FileReportTable(Base):
    '''
    Example rows:
    | id  | project_id | filepath                                          | lines_in_code | date_created               | date_modified              | other columns...   |
    | --- | ---------- | ------------------------------------------------- | ------------- | -------------------------- | -------------------------- | ------------------ |
    | 1   | 1          | /tmp/proj_one/app.py                              | 265           | 2024-11-15 09:45:15.218714 | 2025-03-25 11:53:12.237414 | other statistics...|
    | 2   | 2          | /tmp/proj_two/src/app/page.tsx                    | 189           | 2024-10-28 10:03:59.187515 | 2024-12-14 15:35:54.564158 | other statistics...|
    | 3   | 2          | /tmp/proj_two/src/apps/components/navbar/page.tsx | 122           | 2025-03-26 15:13:29.549154 | 2025-07-12 19:43:22.186141 | other statistics...|
    | 4   | 3          | /tmp/proj_three/clock.py                          | 241           | 2025-01-05 04:48:26.875495 | 2025-10-21 13:51:15.185489 | other statistics...|
    | ... | ...        | ...                                               | ...           | ...                        | ...                        | ...                |
    '''
    __tablename__ = 'file_report'

    id: Mapped[int] = mapped_column(primary_key=True)  # PK
    filepath = mapped_column(String)  # filepath to proj in temp dir

    # Define a FK and many-to-one relationship with ProjectReport.
    # This will allow us to easily find the related file reports that are used to create
    # a given project report
    project_id: Mapped[int] = mapped_column(ForeignKey("project_report.id"))
    project_report: Mapped["ProjectReportTable"] = relationship(
        back_populates="file_reports")
