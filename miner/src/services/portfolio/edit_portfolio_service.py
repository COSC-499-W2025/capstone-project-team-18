"""
Contains the edit portfolio service. The following milestone requirements are:

- Allows users to choose which information is represented (e.g.,
re-ranking of projects, corrections to chronology, attributes for
project comparison, skills to highlight, projects selected for showcase)

- Customize and save information about a portfolio showcase project

"""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from src.database.api.models import BlockModel, PortfolioSectionModel, PortfolioModel
from src.database.api.CRUD.portfolio import get_portfolio_block, sync_domain_block_to_db
from src.utils.errors import KeyNotFoundError


def get_portfolio_conflicts(session: Session, portfolio_id: int) -> list[dict]:
    """
    Returns a list of all blocks currently in a conflict state for a specific portfolio.
    """

    statement = (
        select(BlockModel)
        .join(PortfolioSectionModel)
        .join(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        .where(BlockModel.in_conflict == True)
    )

    conflict_models = session.exec(statement).all()

    return [
        {
            "section_tag": model.section.section_id,  # type: ignore
            "block_tag": model.tag,
            "current_content": model.current_content,
            "conflicting_content": model.conflict_content
        }
        for model in conflict_models
    ]


def resolve_block_accept_system(
    session: Session,
    portfolio_id: int,
    section_tag: str,
    block_tag: str
) -> BlockModel:
    """
    Forces the block to accept the 'conflict_content' as the 'current_content'.
    """

    domain_block = get_portfolio_block(
        session, portfolio_id, section_tag, block_tag)

    if domain_block is None:
        raise KeyNotFoundError(
            f"No block could be found in portfolio {portfolio_id} section {section_tag} block {block_tag}.")

    domain_block.resolve_conflict_accept_system()

    block_model = sync_domain_block_to_db(
        session, portfolio_id, section_tag, block_tag, domain_block)

    session.commit()
    session.refresh(block_model)

    return block_model


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

    portfolio_model.last_updated_at = datetime.now()
    session.add(portfolio_model)
    session.commit()
    session.refresh(portfolio_model)
    return portfolio_model
