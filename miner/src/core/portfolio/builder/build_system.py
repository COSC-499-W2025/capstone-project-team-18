"""
Classes that define a section for a portfolio. This
structure is very similar
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.core.report import UserReport
from src.core.portfolio.portfolio import Portfolio
from src.core.portfolio.sections.portfolio_section import PortfolioSection, merge_section
from src.core.portfolio.sections.block.block import Block
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


class PortfolioSectionBuilder(ABC):
    """
    Abstract base builder for a portfolio section.
    Generates or updates a PortfolioSection based on a report.
    """

    section_id: str
    section_title: str

    @abstractmethod
    def create_blocks(self, report: "UserReport") -> list[Block]:
        """Create blocks for the section"""

    def build(self, report: "UserReport") -> Optional[PortfolioSection]:
        """
        Creates a PortfolioSection for this builder.
        """

        blocks = self.create_blocks(report)

        if len(blocks) == 0:
            return None

        section = PortfolioSection(
            section_id=self.section_id, title=self.section_title)

        for block in blocks:
            section.add_block(block)

        return section

    def update(self, existing_section: PortfolioSection, report: "UserReport") -> PortfolioSection:
        """
        Update an existing section with new report data.
        By default, just regenerate and merge.
        """
        new_section = self.build(report)

        if new_section is None:
            logger.warning("PortfolioSectionBuilder did not generate a new section, but"
                           "wants to merge with another portfolio")
            return existing_section

        merge_section(existing_section, new_section)
        return existing_section


class PortfolioBuilder:
    def __init__(self):
        self.section_builders: list[PortfolioSectionBuilder] = []

    def register_section_builder(self, builder: PortfolioSectionBuilder):
        self.section_builders.append(builder)

    def build(self, report: "UserReport") -> Portfolio:
        portfolio = Portfolio()
        for builder in self.section_builders:
            section = builder.build(report)

            if section is None:
                continue

            portfolio.sections.append(section)
        return portfolio

    def update(self, existing_portfolio: Portfolio, report: "UserReport") -> Portfolio:
        """
        Merge updates into an existing portfolio.
        """

        for builder in self.section_builders:
            # see if section already exists
            section_id = builder.section_id

            existing_section = next(
                (s for s in existing_portfolio.sections if s.id == section_id), None
            )

            if existing_section:
                builder.update(existing_section, report)
            else:
                section = builder.build(report)

                if section is not None:
                    existing_portfolio.sections.append(section)

        return existing_portfolio
