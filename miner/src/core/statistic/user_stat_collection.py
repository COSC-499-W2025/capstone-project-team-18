"""
This document logs all the different USER statistics that can be collected.
"""

from enum import Enum
from datetime import date
from .statistic_models import WeightedSkills, CodingLanguage
from .base_classes import StatisticTemplate


class UserStatisticTemplate(StatisticTemplate):
    pass


class UserStatCollection(Enum):
    USER_START_DATE = UserStatisticTemplate(
        name="USER_START_DATE",
        description="the very first project start",
        expected_type=date,
    )

    USER_END_DATE = UserStatisticTemplate(
        name="USER_END_DATE",
        description="the latest project end",
        expected_type=date,
    )

    USER_SKILLS = UserStatisticTemplate(
        name="USER_SKILLS",
        description="the skills this user has",
        expected_type=list[WeightedSkills],
    )

    USER_CODING_LANGUAGE_RATIO = UserStatisticTemplate(
        name="USER_CODING_LANGUAGE_RATIO",
        description="ratio, by lines of code, of coding languages in the user's projects",
        expected_type=dict[CodingLanguage, float]
    )

    COMMIT_ACTIVITY_TIMELINE = StatisticTemplate(
        name="COMMIT_ACTIVITY_TIMELINE",
        description="Commit counts per day, keyed by ISO date string",
        expected_type=dict  # {"2024-03-01": 3, "2024-03-02": 1, ...}
    )

    TOTAL_COMMIT_ACTIVITY_TIMELINE = StatisticTemplate(
        name="TOTAL_COMMIT_ACTIVITY_TIMELINE",
        description="total commit counts per day in a group project, keyed by ISO date string",
        expected_type=dict  # {"2024-03-01": 3, "2024-03-02": 1, ...}
    )
