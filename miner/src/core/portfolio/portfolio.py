"""
Defines the Portfolio object.
"""
from datetime import datetime
from typing import Optional
from src.core.portfolio.sections.portfolio_section import PortfolioSection


class PortfolioMetadata:
    creation_time: datetime
    last_updated_at: datetime
    project_ids_include: list[int]

    def __init__(self,
                 project_ids: list[int] = [],
                 creation_date: Optional[datetime] = None,
                 last_updated_at: Optional[datetime] = None,
                 ):

        self.creation_time = creation_date or datetime.now()
        self.last_updated_at = last_updated_at or datetime.now()
        self.project_ids_include = project_ids


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
