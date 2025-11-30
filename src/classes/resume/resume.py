"""
This class holds all the logic
for building and managing resumes.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from src.classes.statistic import WeightedSkills
from src.classes.resume.render import *


@dataclass
class ResumeItem:
    """
    A single item for paragraph in resume. It is
    a single project
    """

    title: str
    bullet_points: list[str]
    start_date: date
    end_date: date


class Resume:
    """
    This is the main resume class that holds all the
    resume items and can generate a formatted resume.

    Attributes:
        items (list[ResumeItem]): A list of resume items.
        skills (list[str]): A list of skills.

    """

    # TODO: Expand more attributes like contact info, summary, etc.

    def __init__(self):
        self.items = []
        self.skills = []

    def add_item(self, item: ResumeItem):
        self.items.append(item)

    def add_skill(self, skill: str):
        self.skills.append(skill)

    def export(self, render: ResumeRender) -> str:
        return render.render(self)

    def __str__(self) -> str:
        return self.export(TextResumeRenderer())
