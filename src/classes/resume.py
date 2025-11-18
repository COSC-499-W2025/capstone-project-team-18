"""
This class holds all the logic
for building and managing resumes.
"""

from dataclasses import dataclass
from datetime import date


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

    def generate_resume(self) -> str:
        resume = ""
        for item in self.items:
            resume += f"{item.title} : {item.start_date} - {item.end_date}\n"
            for bullet in item.bullet_points:
                resume += f"   - {bullet}\n"
            resume += "\n"
        return resume

    def __str__(self) -> str:
        return self.generate_resume()
