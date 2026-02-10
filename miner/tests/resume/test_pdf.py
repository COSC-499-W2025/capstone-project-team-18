from datetime import date

from src.core.resume.resume import Resume, ResumeItem
from pathlib import Path
import os


def test_pdf_extraction():
    resume = Resume()
    item = ResumeItem(
        title="Software Engineer",
        frameworks=[],
        bullet_points=["Developed features", "Fixed bugs"],
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1)
    )
    resume.add_item(item)

    resume.to_pdf('test.pdf')
    filepath = Path('test.pdf')

    assert filepath.is_file()

    os.remove(filepath)
