"""
Defines the class structure for building statistics.

This module uses generics so you can write type-safe statistic calculations
for different `BaseReport` subclasses (e.g., `ProjectReport` and `UserReport`).
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Type, Optional

from src.core.statistic import Statistic
from src.infrastructure.log.logging import get_logger
from src.core.report.base_report import BaseReport

logger = get_logger(__name__)


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

    def __init__(
        self,
        master_list: List[Type],
        requested_classes: Optional[List[Type]] = None
    ) -> None:
        """
        Generic initialization logic for all statistic builders. The object
        making the statistic builder may pass in a subset of the requested
        claculators. For example, in the get skills endpoint, we only want
        the UserStatisticReportBuilder to just calculate weighted skills.
        """
        if requested_classes is not None:
            if not requested_classes:
                logger.warning(
                    f"{self.__class__.__name__} called with no requested calculators.")
                self.calculators = []
            else:
                # Filter master list based on requested classes
                self.calculators = [
                    cls() for cls in master_list
                    if cls in requested_classes
                ]
        else:
            # Default to all available calculators
            self.calculators = [cls() for cls in master_list]

        logger.info(
            f"{self.__class__.__name__} initialized with {len(self.calculators)} calculators")

    def build(self, report: TReport) -> list[Statistic]:
        """
        Compile all the project level statistics together into one
        statistic list
        """
        stats: list[Statistic] = []

        for calc in self.calculators:
            new_stats = calc.calculate(report)
            if new_stats:
                report.statistics.extend(new_stats)
                stats.extend(new_stats)

        return stats
