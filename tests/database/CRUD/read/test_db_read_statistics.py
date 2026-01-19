"""
Tests that we can read and recreate specific statistics from the database
"""

import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database.models import ProjectReportTable, FileReportTable
from src.database.utils.database_access import _project_report_from_row
from src.classes.statistic import (
    ProjectStatCollection,
    CodingLanguage,
)
from src.classes.statistic import ProjectStatCollection


def test_project_report_from_row_rebuilds_coding_language_ratio(blank_db):
    engine = blank_db
    with Session(engine) as session:
        proj = ProjectReportTable(
            project_name="proj",
            coding_language_ratio={
                CodingLanguage.PYTHON: 0.6, CodingLanguage.JAVA: 0.4}
        )
        file_row = FileReportTable(
            filepath="a.py",
            lines_in_file=1,
            date_created=datetime.datetime.now(),
            date_modified=datetime.datetime.now(),
            file_size_bytes=1
        )
        proj.file_reports.append(file_row)  # type: ignore
        session.add(proj)
        session.commit()

        row = session.execute(select(ProjectReportTable)).scalar_one()
        pr = _project_report_from_row(row, engine)
        ratio = pr.get_value(ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

        assert ratio.get(CodingLanguage.PYTHON) == 0.6
        assert ratio.get(CodingLanguage.JAVA) == 0.4
