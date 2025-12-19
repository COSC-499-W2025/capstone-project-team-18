"""
Defines the class structure for building statistics.

This module uses generics so you can write type-safe statistic calculations
for different `BaseReport` subclasses (e.g., `ProjectReport` and `UserReport`).
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from src.classes.statistic import Statistic
from src.classes.report.base_report import BaseReport


# Generic type variable constrained to BaseReport (so type checkers know what report type
# a particular StatisticCalculation or StatisticReportBuilder expects)
TReport = TypeVar("TReport", bound=BaseReport)


class StatisticCalculation(ABC, Generic[TReport]):
    """
    Abstract base class for statistic calculations parameterized by report type.

    Subclasses should specify the concrete report type (e.g., `StatisticCalculation[ProjectReport]`).
    """

    @abstractmethod
    def calculate(self, report: TReport) -> list[Statistic]:
        """
        Calculate the statistic based on the provided report instance.
        """
        raise NotImplementedError(
            "Subclasses must implement the calculate method.")


class StatisticReportBuilder(ABC, Generic[TReport]):
    """
    Abstract base class of a Statistic builder parameterized by report type.
    Which aggregates various statistic calculations into a single list of statistics.
    """

    def __init__(self) -> None:
        self.calculators = []

    def build(self, report) -> list[Statistic]:
        stats: list[Statistic] = []

        for calc in self.calculators:
            new_stats = calc.calculate(report)
            if new_stats:
                report.statistics.extend(new_stats)
                stats.extend(new_stats)

        return stats
