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

    DATE_CREATED = FileStatisticTemplate(
        name="DATE_CREATED",
        description="creation date of the file",
        expected_type=date,
    )

    DATE_MODIFIED = FileStatisticTemplate(
        name="DATE_MODIFIED",
        description="last date the file was modified",
        expected_type=date,
    )

    DATE_ACCESSED = FileStatisticTemplate(
        name="DATE_ACCESSED",
        description="last date the file was accessed",
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
    StatisticIndex is a list of multiple Statistic objects.
    It provides methods to add, retrieve, update, and list
    statistics in an organized way.

    At the end of the day, this class is just a wrapper for a hashmap.
    However, it provides a way for us to add functionality as our
    system gets more complex. For example, maybe we want a method here
    to save these statistic to a database. It is simply a
    layer of abstraction.
    """

    _stats: Dict[StatisticTemplate, Statistic]

    def __init__(self, list_of_statistics: Optional[List[Statistic]] = None):
        self._stats = {}

        if list_of_statistics is None:
            return

        for stat in list_of_statistics:
            self.add(stat)

    def add(self, stat: Statistic):
        """
        Adds a Statistic to index.

        If a statistic of this type is already in the index,
        it will overwrite it
        """

        self._stats[stat.get_template()] = stat

    def remove(self, stat: Statistic):
        """
        Removes a Statistic from the index
        """

        self._stats.pop(stat.get_template(), None)

    def get(self, template: StatisticTemplate) -> Optional[Statistic]:
        """
        Retrieves a Statistic from the index by its template.
        Returns None if not found.
        """

        return self._stats.get(template, None)

    def get_value(self, template: StatisticTemplate) -> Any:
        """
        Retrieves the value of a Statistic from the index by its template.
        Returns None if not found.
        """

        stat = self.get(template)
        if stat is None:
            return None
        return stat.value

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the StatisticIndex to a dictionary mapping
        statistic names to their values.
        """

        return {
            stat.get_template().name: stat.value
            for stat in self._stats.values()
        }

    def __len__(self):
        return len(self._stats)

    def __repr__(self):
        stats_repr = ", ".join(
            [f"{stat.get_template().name}={stat.value}" for stat in self._stats.values()]
        )
        return f"<StatisticIndex {stats_repr}>"

    def __iter__(self):
        return iter(self._stats.values())

    def __contains__(self, template: StatisticTemplate) -> bool:
        return template in self._stats
