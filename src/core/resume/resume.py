"""
This class holds all the logic
for building and managing resumes.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional
from src.core.statistic import WeightedSkills
from src.core.resume.render import *
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ResumeItem:
    """
    A single item for paragraph in resume. It is
    a single project
    """

    title: str
    frameworks: list[WeightedSkills]
    bullet_points: list[str]
    start_date: date
    end_date: date

    # Keep only the top three frameworks
    def __post_init__(self):
        self.frameworks = sorted(self.frameworks, reverse=True)[:3]


class Resume:
    """
    This is the main resume class that holds all the
    resume items and can generate a formatted resume.

    Attributes:
        items (list[ResumeItem]): A list of resume items.
        skills (list[str]): A list of skills.

    """

    items: list[ResumeItem]

    def __init__(self, email: Optional[str] = None, github: Optional[str] = None, weight_skills: Optional[list[WeightedSkills]] = None):
        self.items = []
        self.email = email if email else None
        self.github = github if github else None
        self.skills = []

        if weight_skills:

            weight_skills.sort(reverse=True)

            for weighted_skill in weight_skills[:7]:
                self.skills.append(weighted_skill.skill_name)

    def add_item(self, item: ResumeItem):
        self.items.append(item)

    def export(self, render: ResumeRender) -> str:
        return render.render(self)

    def to_pdf(self, filepath='resume.pdf'):
        if not filepath[-4:] == '.pdf':
            filepath = 'resume.pdf'
            logger.info(
                "Incorrect filename format has been replaced by resume.pdf")

        pdf = self.export(PDFRenderer())

        with open(filepath, "wb") as file:
            file.write(pdf)

    def __str__(self) -> str:
        return self.export(TextResumeRenderer())
