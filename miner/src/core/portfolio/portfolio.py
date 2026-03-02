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
    Merges two portfolios. The existing one was generated previously and may or
    may not have user changes. The generated portfolio is the newly generated portfolio.
    We merge on existing adding any sections that werent there previously and merging any
    ones that did.
    """
    existing_map = {sec.id: sec for sec in existing.sections}

    merged_sections = []
    processed_ids = set()

    # Loop through every generated section. Either merge the section
    # if it exists in the existing port. or add that section.
    for updated_section in generated.sections:
        existing_sec = existing_map.get(updated_section.id)
        if existing_sec:
            merged_sections.append(merge_section(
                existing_sec, updated_section))
        else:
            merged_sections.append(updated_section)
        processed_ids.add(updated_section.id)

    # Add any existing sections that was not present in the newly
    # generated section
    for sec_id, sec in existing_map.items():
        if sec_id not in processed_ids:
            merged_sections.append(sec)

    existing.sections = merged_sections
    existing.metadata.last_updated_at = datetime.now()

    return existing
