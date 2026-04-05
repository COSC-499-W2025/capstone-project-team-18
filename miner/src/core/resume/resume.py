"""
This class holds all the logic
for building and managing resumes.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional, List
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
    project_name: Optional[str] = None

    # Keep only the top three frameworks
    def __post_init__(self):
        self.frameworks = sorted(self.frameworks, reverse=True)[:3]

@dataclass
class SkillsByExpertise:
    expert: List[str]
    intermediate: List[str]
    exposure: List[str]

    def has_any(self) -> bool:
        return bool(self.expert or self.intermediate or self.exposure)

class Resume:
    """
    This is the main resume class that holds all the
    resume items and can generate a formatted resume.

    Attributes:
        items (list[ResumeItem]): A list of resume items.
        skills (list[str]): A list of skills.

    """

    items: list[ResumeItem]

    def __init__(
        self,
        email: Optional[str] = None,
        github: Optional[str] = None,
        weight_skills: Optional[list[WeightedSkills]] = None,
        education: Optional[list[str]] = None,
        awards: Optional[list[str]] = None,
        title: Optional[str] = None,
        name: Optional[str] = None,
        location: Optional[str] = None,
        linkedin: Optional[str] = None,
    ):
        self.items = []
        self.email = email if email else None
        self.github = github if github else None
        self.title = title
        self.name = name if name else None
        self.location = location if location else None
        self.linkedin = linkedin if linkedin else None
        self.skills = []
        self.education = education or []
        self.awards = awards or []
        self.weighted_skills = weight_skills or []
        self._skills_by_expertise: Optional[SkillsByExpertise] = None

        if weight_skills:

            weight_skills.sort(reverse=True)

            for weighted_skill in weight_skills[:7]:
                self.skills.append(weighted_skill.skill_name)

    def get_skills_by_expertise(self) -> Optional[SkillsByExpertise]:
        """
        Return skills categorized by expertise level.

        Uses a stored snapshot (e.g. loaded from the database) when available.
        Otherwise computes from weighted_skills using weight thresholds:
        - Expert: weight >= 0.7
        - Intermediate: 0.4 <= weight < 0.7
        - Exposure: weight < 0.4

        Returns None if neither source is available.
        """
        if self._skills_by_expertise is not None:
            return self._skills_by_expertise

        if not self.weighted_skills:
            return None

        expert = []
        intermediate = []
        exposure = []

        for ws in self.weighted_skills:
            if ws.weight >= 0.7:
                expert.append(ws.skill_name)
            elif ws.weight >= 0.4:
                intermediate.append(ws.skill_name)
            else:
                exposure.append(ws.skill_name)

        return SkillsByExpertise(
            expert=expert,
            intermediate=intermediate,
            exposure=exposure
        )

    def add_item(self, item: ResumeItem):
        self.items.append(item)

    def export(self, render: ResumeRender) -> str | bytes:
        return render.render(self)

    def to_pdf(self, filepath='resume.pdf'):
        path = Path(filepath)
        if path.suffix.lower() != ".pdf":
            filepath = str(path.with_suffix(".pdf"))
            logger.info(
                "Incorrect filename format: %s has been replaced by resume.pdf", path)

        pdf: bytes = self.export(PDFRenderer())  # type: ignore

        with open(filepath, "wb") as file:
            file.write(pdf)

    def __str__(self) -> str:
        return self.export(TextResumeRenderer())  # type: ignore
