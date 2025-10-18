"""
This file defines everything that has to do with a statistic. Everything
revolves around the Statistic class.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import date
from typing import Any, List, Dict, Optional
from abc import ABC

# These are data classes. The purpose of these is sometimes a statistic needs
# to hold many types of data instead of just one value. For example, WeightedSkills
# doesn't just have the skill_name, but also a weight attached to it.


@dataclass
class WeightedSkills:
    skill_name: str
    weight: float


class FileDomain(Enum):
    DESIGN = "design"
    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"

# The following are StatisticTemplate classes. A StatisticTemplate is simply a
# description of a data point. It has a name, description, expected value, and it is either
# a statistic about a single file, one project, or the user's behavior.


@dataclass(frozen=True)
class StatisticTemplate(ABC):
    """
    This is the very base template. If we need any metadata
    about a statistic (e.g. description) it lives here.
    """
    name: str
    description: str
    expected_type: Any


class FileStatisticTemplate(StatisticTemplate):
    pass


class ProjectStatisticTemplate(StatisticTemplate):
    pass


class UserStatisticTemplate(StatisticTemplate):
    pass

# The following are a list of stats available at the file, project, and
# user level. If we want to add a new data point, (e.g. you want to keep
# track of the authors in a file) you would give that a name, description,
# and a expected_type and put that in the according Collection class.

# The purpose of these Collection classes is that they serve as the
# ground truth list of all statistics. These collection objects are
# the one single place where we create, delete, and modify the types
# of data points we are dealing with.


class FileStatCollection(Enum):
    LINES_IN_FILE = FileStatisticTemplate(
        name="LINES_IN_FILE",
        description="number of lines in a file",
        expected_type=int,
    )

    DATE_MODIFIED = FileStatisticTemplate(
        name="DATE_MODIFIED",
        description="last date the file was modified",
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


class Statistic():
    """
    The Statistic class is the concrete data holder of a data point that
    was described by a StatisticTemplate.

    A Statistic instance is defined with two objects, a StatisticTemplate
    which defines what data point you are looking at, and a value which is
    the actual value of the stat.

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

    def get_template(self) -> StatisticTemplate:
        return self.statistic_template

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
