from typing import Optional, Any, Dict
from fastapi import APIRouter, Depends
from sqlmodel import Session
from pydantic import BaseModel

from src.services.portfolio.generate_update_portfolio_service import generate_and_save_portfolio, update_portfolio
from src.services.portfolio.edit_portfolio_service import get_portfolio_conflicts, resolve_block_accept_system
from src.database import load_portfolio, update_portfolio_block
from src.interface.api.routers.util import get_session

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
)


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: int, session: Session = Depends(get_session)):
    """
    Retrieve a portfolio by its database ID.

    Path parameters:
    - `portfolio_id`: Integer primary key of the portfolio record.

    Returns:
    - 200: The portfolio object with all sections and blocks.
    """
    return load_portfolio(session, portfolio_id)


class PortfolioRequest(BaseModel):
    project_names: list[str]
    portfolio_title: Optional[str] = None


@router.post("/generate")
def generate_portfolio(request_data: PortfolioRequest):
    """
    Generate and persist a new portfolio from the specified projects.

    Body parameters:
    - `project_names`: List of project names to include in the portfolio.
    - `portfolio_title`: Optional display title for the portfolio.

    Returns:
    - 200: The generated portfolio object with all sections and blocks.
    """
    return generate_and_save_portfolio(
        request_data.project_names,
        request_data.portfolio_title
    )


@router.post("/{portfolio_id}/refresh")
def refresh_portfolio(portfolio_id: int):
    """
    Regenerate the content of an existing portfolio using current project data.

    Path parameters:
    - `portfolio_id`: Integer primary key of the portfolio to refresh.

    Returns:
    - 200: The updated portfolio object.
    """
    return update_portfolio(portfolio_id)


@router.post("/{portfolio_id}/sections/{section_id}/block/{block_tag}/edit")
def edit_portfolio_block(
    portfolio_id: int,
    section_id: str,
    block_tag: str,
    payload: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    Apply a partial update to a specific block within a portfolio section.

    Path parameters:
    - `portfolio_id`: Integer primary key of the portfolio.
    - `section_id`: Tag identifier of the section containing the block.
    - `block_tag`: Tag identifier of the block to edit.

    Body parameters:
    - Any key/value pairs accepted by the block's update logic.

    Returns:
    - 200: The updated block object.
    """
    updated_block = update_portfolio_block(
        session=session,
        portfolio_id=portfolio_id,
        section_tag=section_id,
        block_tag=block_tag,
        **payload
    )
    session.commit()
    return updated_block


@router.get("/{portfolio_id}/conflicts")
def list_conflicts(portfolio_id: int, session: Session = Depends(get_session)):
    """
    Return all blocks currently in a conflict state so the UI can highlight them.

    A block is in conflict when the system-generated version differs from a
    user-saved version and the user has not yet resolved the discrepancy.

    Path parameters:
    - `portfolio_id`: Integer primary key of the portfolio.

    Returns:
    - 200: A list of blocks currently in conflict state.
    """
    return get_portfolio_conflicts(session, portfolio_id)


@router.post("/{portfolio_id}/sections/{section_id}/blocks/{block_tag}/resolve-accept")
def resolve_accept_system(
    portfolio_id: int,
    section_id: str,
    block_tag: str,
    session: Session = Depends(get_session)
):
    """
    Resolve a conflict by accepting the system-generated version of a block.

    Discards the user's saved version and replaces it with the current
    system-generated content, clearing the conflict flag.

    Path parameters:
    - `portfolio_id`: Integer primary key of the portfolio.
    - `section_id`: Tag identifier of the section containing the block.
    - `block_tag`: Tag identifier of the block to resolve.

    Returns:
    - 200: The resolved block object with conflict cleared.
    """
    return resolve_block_accept_system(session, portfolio_id, section_id, block_tag)
