"""
Contains the edit portfolio service.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from src.database.api.models import PortfolioModel
from src.utils.errors import KeyNotFoundError


def edit_portfolio_metadata(
    session: Session,
    portfolio_id: int,
    title: Optional[str] = None,
    project_ids_include: Optional[list[str]] = None,
) -> PortfolioModel:
    """
    Edit portfolio-level metadata: title and project selection.

    This does NOT regenerate content — use POST /portfolio/{id}/refresh for that.
    Only non-None arguments are written.
    """
    statement = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
    portfolio_model = session.exec(statement).first()

    if not portfolio_model:
        raise KeyNotFoundError(f"No portfolio with id {portfolio_id}")

    if title is not None:
        portfolio_model.title = title

    if project_ids_include is not None:
        portfolio_model.project_ids_include = list(project_ids_include)

    portfolio_model.last_updated_at = datetime.now(timezone.utc)
    session.add(portfolio_model)
    session.commit()
    session.refresh(portfolio_model)
    return portfolio_model
