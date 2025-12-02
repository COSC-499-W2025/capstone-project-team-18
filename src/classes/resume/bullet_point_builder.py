"""
This file contains all the logic for the building
the bullet points in the resume. Each bullet point
is described as a 'BulletRule'. The BulletPointBuilder
class will compile all these rules and return a list of
str bullet points
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Protocol, Any
from src.classes.statistic import ProjectStatCollection, StatisticTemplate, CodingLanguage, FileDomain
from src.utils.data_processing import float_to_percent


class ProjectReport(Protocol):
    project_name: str

    @abstractmethod
    def get_value(self, template: StatisticTemplate) -> Any: ...


class BulletRule(ABC):
    """Interface for all bullet rules."""

    @abstractmethod
    def generate(self, report: ProjectReport) -> List[str]:
        """Return 0 or more bullet points."""
        pass


class FallBackRule(BulletRule):
    def generate(self, report: ProjectReport) -> List[str]:
        return [f"I contributued and worked on the project {report.project_name}"]


class ActivityTypeContributionRule(BulletRule):
    def generate(self, report: ProjectReport) -> List[str]:
        """
        This function will log the activity type contribution
        project statistic on the project. If a filedomian contribtion
        was under 5 percent, it will not show

        Args:
            report (ProjectReport): The project report to analyze.

        Returns:
            List[str]: A bullet point for the resume item.
        """

        activity_type: dict[FileDomain, float] = report.get_value(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value)

        if activity_type is None or len(activity_type) == 0:
            return []

        fd_str = []

        for fd, float_percent in activity_type.items():
            if float_percent > 0.05:
                fd_str.append(
                    f"{float_to_percent(float_percent)} on {fd.value}")

        return [f"During the project, I split my contributions between following acitivity types: {", ".join(fd_str)}"]


class WeightedSkillsRule(BulletRule):
    def generate(self, report: ProjectReport) -> List[str]:
        """
        This function generates a bullet point
        for weighted skills demonstrated in the project.
        We take the top 3 weighted skills and list them.

        Args:
            report (ProjectReport): The project report to analyze.

        Returns:
            List[str]: A bullet point for the resume item.
        """

        weighted_skills = report.get_value(
            ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

        if not weighted_skills:
            return []

        sorted_skills = sorted(weighted_skills, key=lambda s: getattr(
            s, 'weight', 0), reverse=True)

        top = sorted_skills[:3]

        return [f"Utilized skills {', '.join([s.skill_name for s in top])}"]


class CodingLanguageRule(BulletRule):
    def generate(self, report: ProjectReport) -> List[str]:
        """
        This function generates a bullet point
        for coding languages used in the project.
        We assume that anything more than (10%) of the code
        is worth mentioning in the resume.

        Args:
            report (ProjectReport): The project report to analyze.

        Returns:
            List[str]: A bullet point for the resume item.
        """

        coding_language_ratio = report.get_value(
            ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

        if not coding_language_ratio:
            return []

        # Consider only languages with at least 10% usage
        lang_ratio: dict[CodingLanguage, float] = {
            lang: frac for lang, frac in coding_language_ratio.items() if frac >= 0.1}

        if len(lang_ratio) == 0:
            return ["Implemented code in small amounts of many programming languages"]

        # If only one language, return
        if len(lang_ratio) == 1:
            for lang in lang_ratio.keys():
                name = lang.value[0]
                return [f"Project was coded using the {name} language"]

        # Multiple languages, get top and others
        top_lang = max(lang_ratio.items(), key=lambda kv: kv[1])[0]
        other_langs = [lang for lang in lang_ratio.keys()
                       if lang != top_lang]

        top_name = top_lang.value[0]
        other_names = [lang.value[0] for lang in other_langs]

        return [f"Implemented code mainly in {top_name} and also in {', '.join(other_names)}"]


class GroupProjectRule(BulletRule):
    def generate(self, report: ProjectReport) -> List[str]:
        """
        Creates a bullet point describing if this project
        was a group project or not. Returns empty if we do
        not have enough information about the project.
        Although, I believe this should never happen.

        Args:
            report (ProjectReport): The project report to analyze.

        Returns:
            List[str]: A bullet point for the resume item.
        """

        is_group = report.get_value(
            ProjectStatCollection.IS_GROUP_PROJECT.value)

        if is_group is True:
            total_authors = report.get_value(
                ProjectStatCollection.TOTAL_AUTHORS.value)

            if total_authors:
                return [f"Collaborated in a team of {total_authors - 1} contributors"]

            return ["Collaborated with multiple contributors"]

        elif is_group is False:
            return ["I individually designed, developed, and led the project"]

        return []


class GitCommitPercentage(BulletRule):
    def generate(self, report: ProjectReport) -> List[str]:

        user_commit_pct = report.get_value(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)

        total_contrib_pct = report.get_value(
            ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)

        to_return = []

        if user_commit_pct is not None:
            to_return.append(f"Authored {user_commit_pct}% of commits")

        if total_contrib_pct is not None:
            to_return.append(
                f"Accounted for {total_contrib_pct}% of total contribution in the final deliverable")

        return to_return


class BulletPointBuilder:
    def __init__(self):
        self.rules: List[BulletRule] = [
            CodingLanguageRule(),
            WeightedSkillsRule(),
            GroupProjectRule(),
            GitCommitPercentage(),
            ActivityTypeContributionRule()
        ]

        self.fallback: BulletRule = FallBackRule()

    def build(self, report: ProjectReport) -> List[str]:
        bullet_points: List[str] = []

        for rule in self.rules:
            bullet_points.extend(rule.generate(report))

        if not bullet_points:
            return self.fallback.generate(report)

        return bullet_points
