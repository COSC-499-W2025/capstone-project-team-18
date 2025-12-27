from dataclasses import dataclass
from typing import Any, List, Dict, Optional, get_origin
from abc import ABC


@dataclass(frozen=True)
class StatisticTemplate(ABC):
    """
    This is the very base template. If we need any metadata
    about a statistic (e.g. description) it lives here.
    """
    name: str
    description: str
    expected_type: Any


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

        # Type validation: Note: this only will catch surface level types: str, int, float, list, dict
        # it will not go deeper then the top level type. For example, this will not catch the difference
        # between a list[str] vs. list[int]

        # Converts generics (e.g list[str]) to their top level type (list)
        origin = get_origin(expected_type)
        top_level_type = origin or expected_type

        if isinstance(top_level_type, type):
            if not isinstance(value, top_level_type):
                raise TypeError(
                    f"{self.statistic_template.name} must be {top_level_type.__name__}, got {type(value).__name__}"
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

    def extend(self, stat_list: List[Statistic]):
        """
        Adds multiple statistics to the index at once.
        """
        for stat in stat_list:
            self.add(stat)

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
