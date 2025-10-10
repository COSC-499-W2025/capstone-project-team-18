"""
A statistic is key information about its subject. It lives in a report
"""

from enum import Enum
from abc import ABC
from dataclasses import dataclass
from datetime import date
from typing import Any, List, Dict, Optional

# These are data classes. They hold data for stats that can't just have one value


@dataclass
class WeightedSkills:
    skill_name: str
    weight: float


class FileDomain(Enum):
    DESIGN = "design"
    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"

# Here are the StatTemplates. They hold the statistics as a Enum.


class StatTemplate(Enum):
    pass


class FileStatTemplate(StatTemplate):
    LINES_IN_FILE = ("number of lines in a file", int)
    DATE_MODIFIED = ("last date the file was modifiyed", date)
    DATE_CREATED = ("creation date of the file", date)
    FILE_SIZE_BYTES = ("number of bytes in the file", int)
    RATIO_OF_INDIVIDUAL_CONTRIBUTION = (
        "amount of the file that was authored by the user", float)
    SKILLS_DEMONSTRATED = (
        "the skills that where demonstrated in this file", list[str])
    TYPE_OF_FILE = (
        "what is the purpose of this file?", FileDomain)


class ProjectStatTemplate(StatTemplate):
    PROJECT_START_DATE = ("the first start date of the project", date)
    PROJECT_END_DATE = ("the last date of the project", date)
    PROJECT_SKILLS_DEMONSTRATED = (
        "the skills demonstrated in this project", list[WeightedSkills])


class UserStatTemplate(StatTemplate):
    USER_START_DATE = ("the very first project start", date)
    USER_END_DATE = ("the latest project end", date)
    USER_SKILLS = ("the skills this user has", list[WeightedSkills])


class Statistic():
    """
    A concrete instance of a statistic described by a StatTemplate.
    """

    def __init__(self, statistic_template: StatTemplate, value: Any):
        self.statistic_template = statistic_template
        expected_type = statistic_template.value[1]

        # Type validation
        if not isinstance(value, expected_type):
            raise ValueError(
                f"Invalid type for {statistic_template.name}: "
                f"expected {expected_type.__name__}, got {type(value).__name__}"
            )

        self.value = value

    def __repr__(self):
        return f"<Statistic {self.statistic_template.name}={self.value}>"


class StatisticIndex():
    """
    This class holds a list of statistics. We define it into its own class
    so under the hood we can use a hashmap to get O(1) lookuptimes.
    """

    def __init__(self, statistics: Optional[List[Statistic]] = None):
        self._statistics: List[Statistic] = statistics or []
        self._index: Dict[StatTemplate, Statistic] = {
            stat.statistic_template: stat for stat in self._statistics
        }

    def add(self, stat: Statistic):
        """Add or update a statistic."""
        self._statistics.append(stat)
        self._index[stat.statistic_template] = stat

    def get(self, template: StatTemplate) -> Optional[Statistic]:
        """Return the full Statistic object if it exists."""
        return self._index.get(template)

    def get_value(self, template: StatTemplate, default=None):
        """Return only the value (or a default if missing)."""
        stat = self.get(template)
        return stat.value if stat else default

    def merge(self, other: "StatisticIndex"):
        """Merge another StatIndex into this one (updates existing keys)."""
        for stat in other._statistics:
            self.add(stat)

    def to_dict(self):
        """Convert to a serializable dictionary."""
        return {s.statistic_template.name: s.value for s in self._statistics}

    def __iter__(self):
        yield from self._statistics

    def __len__(self):
        return len(self._statistics)

    def __repr__(self):
        return f"<StatIndex {self.to_dict()}>"
