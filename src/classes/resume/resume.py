"""
This class holds all the logic
for building and managing resumes.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional
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

    def __init__(self, email: Optional[str] = None, weight_skills: Optional[list[WeightedSkills]] = None):
        self.items = []
        self.email = email if email else None
        self.skills = []

        if weight_skills:

            weight_skills.sort(reverse=True)

            for weighted_skill in weight_skills[:7]:
                self.skills.append(weighted_skill.skill_name)

    def add_item(self, item: ResumeItem):
        self.items.append(item)

    def export(self, render: ResumeRender) -> str:
        return render.render(self)

    def __str__(self) -> str:
        return self.export(TextResumeRenderer())
