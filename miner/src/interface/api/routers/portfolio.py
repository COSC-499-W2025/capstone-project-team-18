from typing import Optional, Any, Dict
from fastapi import APIRouter, Depends, Response
from fastapi import HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from src.services.portfolio.generate_update_portfolio_service import generate_and_save_portfolio, update_portfolio
from src.services.portfolio.edit_portfolio_service import (
    get_portfolio_conflicts,
    resolve_block_accept_system,
    edit_portfolio_metadata,
)
from src.services.portfolio.project_card_service import edit_project_card, set_showcase
from src.services.portfolio.export_service import export_portfolio_static
from src.services.portfolio.github_pages_service import deploy_to_github_pages
from src.database import load_portfolio, update_portfolio_block, get_most_recent_user_config
from src.database.api.CRUD.portfolio import get_project_cards_for_portfolio, list_portfolios, delete_portfolio
from src.interface.api.routers.util import get_session
from src.utils.errors import KeyNotFoundError

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
)


@router.get("")
def get_all_portfolios(session: Session = Depends(get_session)):
    """
    GET /portfolio

    Returns a lightweight list of all portfolios.
    Each entry contains: id, title, creation_time, last_updated_at.
    """
    return {"portfolios": list_portfolios(session)}


@router.delete("/{portfolio_id}")
def remove_portfolio(
    portfolio_id: int,
    session: Session = Depends(get_session),
):
    """
    DELETE /portfolio/{id}

    Permanently deletes a portfolio and all its sections, blocks, and project cards.
    Returns 204 No Content on success, 404 if not found.
    """
    deleted = delete_portfolio(session, portfolio_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Portfolio {portfolio_id} not found")
    session.commit()
    return Response(status_code=204)


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: int, session: Session = Depends(get_session)):
    """
    Retrieve a portfolio by its database ID.

    Returns the full portfolio including all three parts:
      Part A — narrative sections with conflict-aware blocks
      Part B — project cards with is_showcase=True flagged
      Part C — all project cards with rich metadata

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

    Generate a brand new portfolio for the given projects.
    Populates all three parts: narrative sections, project cards (with showcase flags).

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

    Regenerate all auto-populated content (Part A sections + Part C card data).
    User overrides and is_showcase flags are preserved.

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


class EditPortfolioRequest(BaseModel):
    title: Optional[str] = None
    project_ids_include: Optional[list[str]] = None


@router.post("/{portfolio_id}/edit")
def edit_portfolio(
    portfolio_id: int,
    request: EditPortfolioRequest,
    session: Session = Depends(get_session),
):
    """
    POST /portfolio/{id}/edit

    Edit portfolio-level metadata (title, project selection).
    Does NOT regenerate content — use /refresh for that.
    """
    try:
        return edit_portfolio_metadata(
            session,
            portfolio_id,
            title=request.title,
            project_ids_include=request.project_ids_include,
        )
    except KeyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{portfolio_id}/cards")
def get_cards(
    portfolio_id: int,
    themes: Optional[str] = None,   # comma-separated
    tones: Optional[str] = None,
    tags: Optional[str] = None,
    skills: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    GET /portfolio/{id}/cards

    Returns all project cards for the portfolio (Part C gallery).
    Showcase cards (is_showcase=True) are listed first.

    Supports optional comma-separated query params:
      ?themes=web,ml
      ?tones=professional
      ?tags=python,api
      ?skills=React
    """
    theme_list = [t.strip() for t in themes.split(",")] if themes else None
    tone_list = [t.strip() for t in tones.split(",")] if tones else None
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    skill_list = [s.strip() for s in skills.split(",")] if skills else None

    cards = get_project_cards_for_portfolio(
        session, portfolio_id,
        themes=theme_list,
        tones=tone_list,
        tags=tag_list,
        skills=skill_list,
    )
    return {"portfolio_id": portfolio_id, "cards": cards, "count": len(cards)}


class EditCardRequest(BaseModel):
    title_override: Optional[str] = None
    summary_override: Optional[str] = None
    tags_override: Optional[list[str]] = None


@router.patch("/{portfolio_id}/cards/{project_name}")
def patch_card(
    portfolio_id: int,
    project_name: str,
    request: EditCardRequest,
    session: Session = Depends(get_session),
):
    """
    PATCH /portfolio/{id}/cards/{project_name}

    Edit user overrides on a project card (title, summary, tags).
    Auto-populated fields (themes, tones, skills, etc.) are not affected.
    """
    try:
        return edit_project_card(
            session, portfolio_id, project_name,
            title_override=request.title_override,
            summary_override=request.summary_override,
            tags_override=request.tags_override,
        )
    except KeyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


class ShowcaseToggleRequest(BaseModel):
    is_showcase: bool


@router.post("/{portfolio_id}/cards/{project_name}/showcase")
def toggle_showcase(
    portfolio_id: int,
    project_name: str,
    request: ShowcaseToggleRequest,
    session: Session = Depends(get_session),
):
    """
    POST /portfolio/{id}/cards/{project_name}/showcase

    Set or clear the showcase flag on a project card.
    Showcase cards are highlighted yellow and float to the top of the gallery.
    This flag is preserved across portfolio refreshes.
    """
    try:
        return set_showcase(session, portfolio_id, project_name, request.is_showcase)
    except KeyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{portfolio_id}/export")
async def export_portfolio(
    portfolio_id: int,
    session: Session = Depends(get_session),
):
    """
    GET /portfolio/{id}/export

    If the user has a GitHub access token stored, deploys the portfolio as a
    GitHub Pages site and returns the Pages URL as JSON.

    Falls back to returning the static bundle as a ZIP download when no
    GitHub access token is present.

    Returns (GitHub auth present):
        {"pages_url": "https://{username}.github.io/portfolio"}

    Returns (no GitHub auth):
        ZIP archive — Content-Disposition: attachment; filename="portfolio_{id}.zip"
    """
    try:
        zip_bytes = export_portfolio_static(portfolio_id, session)
    except KeyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    user_config = get_most_recent_user_config(session)
    access_token = user_config.access_token if user_config else None

    if access_token:
        pages_url = await deploy_to_github_pages(access_token, zip_bytes)
        return {"pages_url": pages_url}

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="portfolio_{portfolio_id}.zip"'
        },
    )
