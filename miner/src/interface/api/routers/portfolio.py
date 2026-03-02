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
    return load_portfolio(session, portfolio_id)


class PortfolioRequest(BaseModel):
    project_names: list[str]
    portfolio_title: Optional[str] = None


@router.post("/generate")
def generate_portfolio(request_data: PortfolioRequest):
    return generate_and_save_portfolio(
        request_data.project_names,
        request_data.portfolio_title
    )


@router.post("/{portfolio_id}/refresh")
def refresh_portfolio(portfolio_id: int):
    return update_portfolio(portfolio_id)


@router.post("/{portfolio_id}/sections/{section_id}/block/{block_tag}/edit")
def edit_portfolio_block(
    portfolio_id: int,
    section_id: str,
    block_tag: str,
    payload: Dict[str, Any],
    session: Session = Depends(get_session)
):
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
    Returns all blocks currently in a conflict state so the UI can highlight them.
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
    Resolve a conflict by choosing the system-generated version.
    """
    return resolve_block_accept_system(session, portfolio_id, section_id, block_tag)
