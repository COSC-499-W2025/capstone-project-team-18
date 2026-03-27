"""
This file contains all the logic for the building
the bullet points in the resume. Each bullet point
is described as a 'BulletRule'. The BulletPointBuilder
class will compile all these rules and return a list of
str bullet points
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Protocol

from src.core.ML.models.readme_analysis.permissions import \
    ml_extraction_allowed
from src.core.statistic import (CodingLanguage, FileDomain,
                                ProjectStatCollection, StatisticTemplate)
from src.utils.data_processing import float_to_percent


class ProjectReport(Protocol):
    project_name: str

    @abstractmethod
    def get_value(self, template: StatisticTemplate) -> Any: ...


class BulletPoint(ABC):
    """Interface for all bullet rules."""

    @abstractmethod
    def generate(self, report: ProjectReport) -> List[str]:
        """Return 0 or more bullet points."""
        pass


class FallBackRule(BulletPoint):
    def generate(self, report: ProjectReport) -> List[str]:
        return [f"Contributed to and developed the project {report.project_name}"]


class ActivityTypeContributionBulletPoint(BulletPoint):
    def generate(self, report: ProjectReport) -> List[str]:
        """
        This function will log the activity type contribution
        project statistic on the project. If a filedomain contribution
        was under 5 percent, it will not show. If the bullet point would
        only list one file domain (like code), it will not show

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

        if len(fd_str) <= 1:
            return []

        return [f"Directed contributions across {', '.join(fd_str)}"]


class WeightedSkillsBulletPoint(BulletPoint):
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

        return [f"Applied {', '.join([s.skill_name for s in top])} to deliver project outcomes"]


class CodingLanguageBulletPoint(BulletPoint):
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
                name = lang.value
                return [f"Built the project utilizing {name}"]

        # Multiple languages, get top and others
        top_lang = max(lang_ratio.items(), key=lambda kv: kv[1])[0]
        other_langs = [lang for lang in lang_ratio.keys()
                       if lang != top_lang]

        top_name = top_lang.value
        other_names = [lang.value for lang in other_langs]

        return [f"Implemented code mainly in {top_name} and also in {', '.join(other_names)}"]


class GroupProjectBulletPoint(BulletPoint):
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
            return ["Independently designed, developed, and led the project end-to-end"]

        return []


class GitCommitPercentageBulletPoint(BulletPoint):
    def generate(self, report: ProjectReport) -> List[str]:

        user_commit_pct = report.get_value(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)

        is_group = report.get_value(
            ProjectStatCollection.IS_GROUP_PROJECT.value)

        total_contrib_pct = report.get_value(
            ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)

        if is_group is False:
            total_contrib_pct = 100.0

        # Pick whichever percentage is higher; emit only one bullet
        commit_val = user_commit_pct if user_commit_pct is not None else -1
        contrib_val = total_contrib_pct if total_contrib_pct is not None else -1

        if commit_val == -1 and contrib_val == -1:
            return []

        if contrib_val >= commit_val:
            return [f"Delivered {total_contrib_pct}% of the total project contribution"]

        return [f"Drove {user_commit_pct}% of all commits throughout the project lifecycle"]


class ContributionPatternBulletPoint(BulletPoint):
    """Create bullets from contribution-pattern statistics."""

    _WORK_PATTERN_PHRASES: dict[str, str] = {
        "consistent": "Maintained a consistent and reliable contribution cadence",
        "sprint_based": "Delivered work in focused sprints with concentrated commit bursts",
        "burst": "Contributed in concentrated bursts of high productivity",
        "sporadic": "Made targeted contributions across key project milestones",
    }

    _COMMIT_TYPE_PHRASES: dict[str, str] = {
        "feat": "Spearheaded feature development",
        "fix": "Resolved bugs and technical issues",
        "refactor": "Improved code quality through refactoring",
        "docs": "Maintained comprehensive documentation",
        "chore": "Managed project maintenance",
    }

    def generate(self, report: ProjectReport) -> List[str]:
        if not ml_extraction_allowed():
            return []

        bullets: List[str] = []

        collab_role = report.get_value(
            ProjectStatCollection.COLLABORATION_ROLE.value)
        if collab_role:
            role_bullet = self._role_to_bullet(
                str(getattr(collab_role, "value", collab_role)))
            if role_bullet:
                bullets.append(role_bullet)

        work_pattern = report.get_value(
            ProjectStatCollection.WORK_PATTERN.value)
        activity = report.get_value(
            ProjectStatCollection.ACTIVITY_METRICS.value) or {}
        commits_per_week = activity.get("avg_commits_per_week")
        if work_pattern and commits_per_week is not None:
            bullets.append(
                f"Maintained a {str(work_pattern).replace('_', ' ')} cadence with {commits_per_week:.1f} commits/week"
            )
        elif work_pattern:
            key = str(work_pattern).replace(" ", "_").lower()
            phrase = self._WORK_PATTERN_PHRASES.get(
                key,
                f"Maintained a {str(work_pattern).replace('_', ' ')} contribution cadence"
            )
            bullets.append(phrase)

        commit_dist = report.get_value(
            ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value)
        if commit_dist:
            filtered = {k: v for k, v in commit_dist.items()
                        if k.lower() != "unknown" and v > 0}
            top = sorted(filtered.items(), key=lambda kv: kv[1], reverse=True)
            if top:
                primary_phrase = self._COMMIT_TYPE_PHRASES.get(
                    top[0][0].lower(), f"Contributed through {top[0][0]}")
                if len(top) > 1 and top[1][1] > 0:
                    secondary_phrase = self._COMMIT_TYPE_PHRASES.get(
                        top[1][0].lower(), f"contributed {top[1][0]}")
                    bullets.append(
                        f"{primary_phrase} ({top[0][1]:.0f}% of commits), "
                        f"with secondary focus on {secondary_phrase.lower()} ({top[1][1]:.0f}%)"
                    )
                else:
                    bullets.append(
                        f"{primary_phrase} ({top[0][1]:.0f}% of commits)")

        return bullets

    def _role_to_bullet(self, role: str) -> str | None:
        """Map a COLLABORATION_ROLE string to a concise resume bullet using keyword matching."""
        r = role.lower()
        if "leader" in r or "lead" in r:
            return "Led the team as primary contributor and integration manager"
        if "core" in r or "maintainer" in r:
            return "Served as a core contributor, managing key features and stability"
        if "specialist" in r or "expert" in r:
            return "Applied specialized expertise across critical project components"
        return None  # occasional, solo, unknown → skip


class ProjectThemesBulletPoint(BulletPoint):
    """Creates a bullet from ML-extracted project themes."""

    def generate(self, report: ProjectReport) -> List[str]:
        if not ml_extraction_allowed():
            return []

        themes = report.get_value(ProjectStatCollection.PROJECT_THEMES.value)
        if not themes:
            return []

        # cap at 2 to avoid overly long bullet
        theme_list = [str(t) for t in themes[:2]]

        if len(theme_list) == 1:
            return [f"Developed solutions in {theme_list[0]}"]

        return [f"Developed solutions spanning {theme_list[0]} and {theme_list[1]}"]


class BulletPointBuilder:
    def __init__(self):
        self.rules: List[BulletPoint] = [
            CodingLanguageBulletPoint(),
            WeightedSkillsBulletPoint(),
            GroupProjectBulletPoint(),
            GitCommitPercentageBulletPoint(),
            ActivityTypeContributionBulletPoint(),
            ContributionPatternBulletPoint(),
            ProjectThemesBulletPoint(),
        ]

        self.fallback: BulletPoint = FallBackRule()

    def build(self, report: ProjectReport) -> List[str]:
        bullet_points: List[str] = []

        for rule in self.rules:
            bullet_points.extend(rule.generate(report))

        if not bullet_points:
            return self.fallback.generate(report)

        return bullet_points
