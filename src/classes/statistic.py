"""
A statistic is key information about its subject. It lives in a report
"""

from enum import Enum
from dataclasses import dataclass
from datetime import date
from typing import Any, List, Dict, Optional
from abc import ABC

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


@dataclass(frozen=True)
class StatisticTemplate(ABC):
    name: str
    description: str
    expected_type: Any


class FileStatisticTemplate(StatisticTemplate):
    pass


class ProjectStatisticTemplate(StatisticTemplate):
    pass


class UserStatisticTemplate(StatisticTemplate):
    pass


class FileStatisticTemplateCollection(Enum):
    LINES_IN_FILE = FileStatisticTemplate(
        name="LINES_IN_FILE",
        description="number of lines in a file",
        expected_type=int,
    )

    DATE_MODIFIED = FileStatisticTemplate(
        name="DATE_MODIFIED",
        description="last date the file was modifiyed",
        expected_type=date,
    )

    DATE_CREATED = FileStatisticTemplate(
        name="DATE_CREATED",
        description="creation date of the file",
        expected_type=date,
    )

    FILE_SIZE_BYTES = FileStatisticTemplate(
        name="FILE_SIZE_BYTES",
        description="number of bytes in the file",
        expected_type=int,
    )

    RATIO_OF_INDIVIDUAL_CONTRIBUTION = FileStatisticTemplate(
        name="RATIO_OF_INDIVIDUAL_CONTRIBUTION",
        description="amount of the file that was authored by the user",
        expected_type=float,
    )

    SKILLS_DEMONSTRATED = FileStatisticTemplate(
        name="SKILLS_DEMONSTRATED",
        description="the skills that where demonstrated in this file",
        expected_type=list[str],
    )

    TYPE_OF_FILE = FileStatisticTemplate(
        name="TYPE_OF_FILE",
        description="what is the purpose of this file?",
        expected_type=FileDomain,
    )


class ProjectStatisticTemplateCollection(Enum):
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


class UserStatisticTemplateCollection(Enum):
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


class Statistic():
    """
    A concerte application of a statistic described by a StatTemplate.
    """

    def __init__(self, stat_template: StatisticTemplate, value: Any):
        self.statistic_template = stat_template
        expected_type = stat_template.expected_type

        # Type validation: Note: this only will catch simple types: str, int, float
        # It will not catch more complex things like list, dict etc
        if isinstance(expected_type, type):
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"{self.statistic_template.name} must be {expected_type.__name__}, got {type(value).__name__}"
                )

        self.value = value

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.statistic_template.name}={self.value}>"


class StatisticIndex():
    """
    A generic statistic index that holds only one specific type of statistic.
    Uses generics to ensure type safety.
    """

    def __init__(self, statistics: Optional[List[Statistic]] = None):
        self._statistics: List[Statistic] = statistics or []
        self._index: Dict[StatisticTemplate, Statistic] = {
            stat.statistic_template: stat for stat in self._statistics
        }

    def add(self, stat: Statistic) -> None:
        """
        Adds a statistic to to this index. Overwrites any
        duplicaties
        """

        if self._index.get(stat.statistic_template) is not None:
            self._statistics = [
                s for s in self._statistics if s.statistic_template != stat.statistic_template
            ]

        self._statistics.append(stat)
        self._index[stat.statistic_template] = stat

    def add_list(self, stat: list[Statistic]) -> None:
        for s in stat:
            self.add(s)

    def get(self, template: StatisticTemplate) -> Optional[Statistic]:
        """
        Gets a stat from this index by it's template. If the template
        is not present in the index, it will return None.
        """
        return self._index.get(template)

    def get_value(self, template: StatisticTemplate) -> Any:
        """
        Gets the value of a statistic by its template.
        """
        stat = self.get(template)
        return stat.value if stat else None

    def to_dict(self) -> Dict[str, Any]:
        return {s.statistic_template.name: s.value for s in self._statistics}

    def __len__(self) -> int:
        return len(self._statistics)

    def all_statstics(self):
        return self._statistics

    def __repr__(self) -> str:
        return f"<StatisticIndex {self.to_dict()}>"
