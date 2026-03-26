"""
Defines the ProjectCard domain object.

Each ProjectCard represents one project's metadata within a specific portfolio.
It is auto-populated from project statistics on generation/refresh and can be
partially overridden by the user on a per-portfolio basis.

The is_showcase flag marks a card as a highlighted showcase project (Part B).
Showcase cards float to the top and are highlighted in the web portfolio export.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class ProjectCard:
    """
    Portfolio-scoped snapshot of a project's metadata for display in the gallery.

    Auto-populated fields are refreshed on every portfolio refresh.
    Override fields are set by the user and are never overwritten by the system.
    The is_showcase flag is user-controlled and never overwritten on refresh.
    """
    portfolio_id: int
    project_name: str

    # Auto-populated from project statistics (base64-encoded string, or None)
    image_data: Optional[str] = None
    summary: str = ""
    themes: list[str] = field(default_factory=list)
    tones: str = ""                          # single dominant tone string
    tags: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    languages: dict = field(default_factory=dict)   # {language_name: ratio_float}
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_group_project: bool = False
    collaboration_role: str = ""
    work_pattern: str = ""
    commit_type_distribution: dict = field(default_factory=dict)
    activity_metrics: dict = field(default_factory=dict)

    # Part B showcase flag — user-controlled, preserved across refreshes
    is_showcase: bool = False

    # User-editable overrides — never overwritten by system on refresh
    title_override: Optional[str] = None
    summary_override: Optional[str] = None
    tags_override: Optional[list[str]] = None

    last_user_edit_at: Optional[datetime] = None
