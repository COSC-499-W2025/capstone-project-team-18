'''
The portfolio table will store the formatted text versions of portfolios, so that when the user
modifies a portfolio, we have a way to keep that edit persistent. It has a one-to-one
relationship with the `user_report` table.
'''
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.resume.resume import Resume

from src.database.utils.init_columns import make_columns
from src.database.models.user_report_table import UserReportTable
from src.database.base import Base


@make_columns(Resume)
class PortfolioTable(Base):
    __tablename__ = 'portfolio'

    id: Mapped[int] = mapped_column(primary_key=True)  # PK

    user_report_id: Mapped[int] = mapped_column(ForeignKey("user_report.id"))
    user_report: Mapped['UserReportTable'] = relationship(
        back_populates="portfolios")
