"""
Defines the Portfolio object.
"""
from datetime import datetime
from typing import Optional
from src.core.portfolio.sections.portfolio_section import PortfolioSection, merge_section


class PortfolioMetadata:
    creation_time: datetime
    last_updated_at: datetime
    project_ids_include: list[str]

    def __init__(self,
                 project_ids: list[str] = [],
                 creation_date: Optional[datetime] = None,
                 last_updated_at: Optional[datetime] = None,
                 ):

        self.creation_time = creation_date or datetime.now()
        self.last_updated_at = last_updated_at or datetime.now()
        self.project_ids_include = list(project_ids)


class Portfolio:
    """
    This is the master class for the portfolio object. It
    only holds user ready content (text, image, etc). It does
    not hold user statistics.
    """

    metadata: PortfolioMetadata
    sections: list[PortfolioSection]
    title: str

    def __init__(self, sections: Optional[list[PortfolioSection]] = None, metadata: Optional[PortfolioMetadata] = None, title: str = "My Portfolio"):
        self.sections = sections or []
        self.metadata = metadata or PortfolioMetadata([])
        self.title = title
        pass

    def render(self) -> str:
        """Render the entire portfolio as a string by rendering each section."""
        lines = [
            f"Portfolio (created {self.metadata.creation_time:%Y-%m-%d})\n"]
        for section in self.sections:
            lines.append(f"## {section.title}\n")
            lines.append(section.render())
        return "\n".join(lines)


def merge_portfolios(existing: Portfolio, generated: Portfolio) -> Portfolio:
    """
    Merges two portfolios. The existing one was generated previously
    """

    # Merge the sections together
    merged_sections = []
    for updated_section in generated.sections:
        existing_section = next(
            (sec for sec in existing.sections if sec.id == updated_section.id), None)

        if existing_section is None:
            merged_sections.append(updated_section)
        else:
            merged_sections.append(merge_section(
                existing_section, updated_section))

    # Update the existing portfolio
    existing.sections = merged_sections
    existing.metadata.last_updated_at = datetime.now()

    return existing
