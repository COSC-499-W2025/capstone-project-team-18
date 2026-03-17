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
from src.database import load_portfolio, update_portfolio_block
from src.database.api.CRUD.portfolio import get_project_cards_for_portfolio
from src.interface.api.routers.util import get_session
from src.utils.errors import KeyNotFoundError

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
)


# ---------------------------------------------------------------------------
# Existing endpoints (preserved)
# ---------------------------------------------------------------------------

@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: int, session: Session = Depends(get_session)):
    """
    GET /portfolio/{id}

    Returns the full portfolio including all three parts:
      Part A — narrative sections with conflict-aware blocks
      Part B — project cards with is_showcase=True flagged
      Part C — all project cards with rich metadata
    """
    return load_portfolio(session, portfolio_id)


class PortfolioRequest(BaseModel):
    project_names: list[str]
    portfolio_title: Optional[str] = None


@router.post("/generate")
def generate_portfolio(request_data: PortfolioRequest):
    """
    POST /portfolio/generate

    Generate a brand new portfolio for the given projects.
    Populates all three parts: narrative sections, project cards (with showcase flags).
    """
    return generate_and_save_portfolio(
        request_data.project_names,
        request_data.portfolio_title
    )


@router.post("/{portfolio_id}/refresh")
def refresh_portfolio(portfolio_id: int):
    """
    POST /portfolio/{id}/refresh

    Regenerate all auto-populated content (Part A sections + Part C card data).
    User overrides and is_showcase flags are preserved.
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


# ---------------------------------------------------------------------------
# New endpoints
# ---------------------------------------------------------------------------

class EditPortfolioRequest(BaseModel):
    title: Optional[str] = None
    mode: Optional[str] = None               # "private" | "public"
    project_ids_include: Optional[list[str]] = None


@router.post("/{portfolio_id}/edit")
def edit_portfolio(
    portfolio_id: int,
    request: EditPortfolioRequest,
    session: Session = Depends(get_session),
):
    """
    POST /portfolio/{id}/edit

    Edit portfolio-level metadata (title, mode, project selection).
    Does NOT regenerate content — use /refresh for that.

    mode: "private" = editable via API; "public" = read-only (static export)
    """
    try:
        return edit_portfolio_metadata(
            session,
            portfolio_id,
            title=request.title,
            mode=request.mode,
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
def export_portfolio(
    portfolio_id: int,
    session: Session = Depends(get_session),
):
    """
    GET /portfolio/{id}/export

    Download a self-contained static web portfolio as a ZIP archive.
    The ZIP contains: index.html, portfolio_data.js, style.css, filter.js

    This is the "public mode" deliverable — the static bundle supports
    client-side search and filter with no server required.
    """
    try:
        zip_bytes = export_portfolio_static(portfolio_id, session)
    except KeyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="portfolio_{portfolio_id}.zip"'
        },
    )
