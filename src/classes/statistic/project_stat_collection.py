"""
This document logs all the different PROJECT statistics that can be collected.
"""

from enum import Enum
from datetime import date
from .statistic_models import WeightedSkills, CodingLanguage, FileDomain
from .base_classes import StatisticTemplate


class ProjectStatisticTemplate(StatisticTemplate):
    pass


class ProjectStatCollection(Enum):
    PROJECT_START_DATE = ProjectStatisticTemplate(
        name="PROJECT_START_DATE",
        description="the first start date of the project",
        expected_type=date,
    )

    PROJECT_END_DATE = ProjectStatisticTemplate(
        name="PROJECT_END_DATE",
        description="the last date of the project",
        expected_type=date,
    )

    PROJECT_SKILLS_DEMONSTRATED = ProjectStatisticTemplate(
        name="PROJECT_SKILLS_DEMONSTRATED",
        description="the skills demonstrated in this project",
        expected_type=list[WeightedSkills],
    )

    IS_GROUP_PROJECT = ProjectStatisticTemplate(
        name="IS_GROUP_PROJECT",
        description="whether the project is a group project",
        expected_type=bool,
    )

    TOTAL_AUTHORS = ProjectStatisticTemplate(
        name="TOTAL_AUTHORS",
        description="total number of authors in the project",
        expected_type=int,
    )

    AUTHORS_PER_FILE = ProjectStatisticTemplate(
        name="AUTHORS_PER_FILE",
        description="number of authors per file in the project",
        expected_type=dict,
    )

    USER_COMMIT_PERCENTAGE = ProjectStatisticTemplate(
        name="USER_COMMIT_PERCENTAGE",
        description="percentage of commits authored by user in a Git-tracked project",
        expected_type=float,
    )

    TOTAL_CONTRIBUTION_PERCENTAGE = ProjectStatisticTemplate(
        name="TOTAL_CONTRIBUTION_PERCENTAGE",
        description="percentage of lines authored by user in a Git-tracked project",
        expected_type=float,
    )

    CODING_LANGUAGE_RATIO = ProjectStatisticTemplate(
        name="CODING_LANGUAGE_RATIO",
        description="ratio, by lines of code, of coding languages in a project",
        expected_type=dict[CodingLanguage, float]
    )

    TOTAL_PROJECT_LINES = ProjectStatisticTemplate(
        name="TOTAL_PROJECT_LINES",
        description="Total lines contained in a project",
        expected_type=int
    )

    ACTIVITY_TYPE_CONTRIBUTIONS = ProjectStatisticTemplate(
        name="ACTIVITY_TYPE_CONTRIBUTIONS",
        description="The user's contributions to each file domain",
        expected_type=dict[FileDomain, float]
    )

    PROJECT_FRAMEWORKS = ProjectStatisticTemplate(
        name="PROJECT_FRAMEWORKS",
        description="These are the imported packages",
        expected_type=list[WeightedSkills]
    )

    PROJECT_TAGS = ProjectStatisticTemplate(
        name="PROJECT_TAGS",
        description="key phrases extracted from README content across the project",
        expected_type=list[str]
    )

    PROJECT_THEMES = ProjectStatisticTemplate(
        name="PROJECT_THEMES",
        description="themes inferred from README content across the project",
        expected_type=list[str]
    )

    PROJECT_TONE = ProjectStatisticTemplate(
        name="PROJECT_TONE",
        description="dominant tone inferred from README content across the project",
        expected_type=str
    )
