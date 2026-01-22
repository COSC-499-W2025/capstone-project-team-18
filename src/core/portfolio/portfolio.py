"""
Defines the Portfolio object.
"""
from datetime import datetime
from abc import ABC, abstractmethod
from src.core.report import UserReport


class PortfolioSection(ABC):
    """
    A portfolio is made of sections. This class is a section
    for a portfolio.
    """
    key: str            # stable DB key
    title: str          # human-facing title
    order: int = 0      # default ordering

    @abstractmethod
    def build(self, report: "UserReport") -> dict:
        """
        Returns a serializable structure:
        {
            "key": str,
            "title": str,
            "content": Any
        }
        """
        raise NotImplementedError


class PortfolioMetadata():
    creation_date: datetime
    last_updated_at: datetime


class Portfolio():
    metadata: PortfolioMetadata

    def __init__(self, sections: list[dict]):
        self.sections = sections

    def to_dict(self) -> dict:
        return {"sections": self.sections}

    @DeprecationWarning
    def to_user_string(self) -> str:
        lines = []
        for section in self.sections:
            lines.append(section["title"])
            lines.append("-" * len(section["title"]))
            lines.extend(section["content"])
            lines.append("")
        return "\n".join(lines)
