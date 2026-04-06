"""
Service for editing portfolio project cards (Part C) and managing the showcase
flag (Part B).

Each project card is portfolio-scoped. Auto-populated fields are refreshed on
portfolio refresh. User override fields and the is_showcase flag are preserved
across refreshes and are only changed through these service functions.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Session

from src.database.api.CRUD.portfolio import get_project_card_model
from src.database.api.models import PortfolioProjectCardModel
from src.utils.errors import KeyNotFoundError


def edit_project_card(
    session: Session,
    portfolio_id: int,
    project_name: str,
    title_override: Optional[str] = None,
    summary_override: Optional[str] = None,
    tags_override: Optional[list[str]] = None,
    skills: Optional[list[str]] = None,
    themes: Optional[list[str]] = None,
    tones: Optional[str] = None,
    frameworks: Optional[list[str]] = None,
) -> PortfolioProjectCardModel:
    """
    Apply user overrides to a project card. Only non-None arguments are written.
    Sets last_user_edit_at to now.

    title_override / summary_override / tags_override are preserved across portfolio refreshes.
    skills / themes / tones are written directly and will be overwritten on portfolio refresh.
    """
    model = get_project_card_model(session, portfolio_id, project_name)
    if not model:
        raise KeyNotFoundError(
            f"No project card for '{project_name}' in portfolio {portfolio_id}"
        )

    if title_override is not None:
        model.title_override = title_override
    if summary_override is not None:
        model.summary_override = summary_override
    if tags_override is not None:
        model.tags_override = list(tags_override)
    if skills is not None:
        model.skills = list(skills)
    if themes is not None:
        model.themes = list(themes)
    if tones is not None:
        model.tones = tones
    if frameworks is not None:
        model.frameworks = list(frameworks)

    model.last_user_edit_at = datetime.now()
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def set_showcase(
    session: Session,
    portfolio_id: int,
    project_name: str,
    is_showcase: bool,
) -> PortfolioProjectCardModel:
    """
    Set or clear the is_showcase flag on a project card.
    Does not touch any other field.
    """
    model = get_project_card_model(session, portfolio_id, project_name)
    if not model:
        raise KeyNotFoundError(
            f"No project card for '{project_name}' in portfolio {portfolio_id}"
        )

    model.is_showcase = is_showcase
    session.add(model)
    session.commit()
    session.refresh(model)
    return model
