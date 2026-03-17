from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from typing import Optional

from src.core.portfolio.sections.block.block import Block
from src.database.core.model_serializer import serialize_block, serialize_project_card
from src.database.core.model_deserializer import deserialize_block
from src.database.api.models import PortfolioModel, PortfolioSectionModel, BlockModel, PortfolioProjectCardModel
from src.core.portfolio.portfolio import Portfolio, PortfolioSection
from src.database.core.model_serializer import serialize_portfolio, serialize_portfolio_section
from src.database.core.model_deserializer import deserialize_portfolio
from src.utils.errors import KeyNotFoundError


def save_portfolio(session: Session, portfolio: Portfolio) -> PortfolioModel:
    """
    Saves a portfolio to the database. Assumes this portfolio is a new portfolio,
    and is not updating an existing portfolio.

    Uses a two-phase save: flush first to obtain the portfolio PK, then write
    project_cards which reference that PK via portfolio_id.
    """

    portfolio_model = serialize_portfolio(portfolio)
    session.add(portfolio_model)
    session.flush()  # assigns portfolio_model.id without committing

    for card in (portfolio.project_cards or []):
        card_model = serialize_project_card(card, portfolio_model.id)
        session.add(card_model)

    return portfolio_model


def load_portfolio(session: Session, portfolio_id: int) -> Portfolio | None:
    """
    Retrieves the portfolio for a specific user and converts it back
    into a Domain Portfolio object.

    Uses joinedload to fetch Sections and Blocks in a single hit.
    """

    # We use joinedload to prevent N+1 query problems
    # This fetches Portfolio -> Sections -> Blocks + project_cards in one go
    statement = (
        select(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        .options(
            joinedload(PortfolioModel.sections)  # pyright: ignore
            .joinedload(PortfolioSectionModel.blocks),  # pyright: ignore
            joinedload(PortfolioModel.project_cards),  # pyright: ignore
        )
    )

    portfolio_model = session.exec(statement).unique().first()

    if not portfolio_model:
        return None

    return deserialize_portfolio(portfolio_model)


def get_portfolio_block_model(
    session: Session,
    portfolio_id: int,
    section_tag: str,
    block_tag: str,
) -> Optional[BlockModel]:
    """
    Get a specific block from a portfolio
    """
    statement = (
        select(BlockModel)
        .join(PortfolioSectionModel)
        .join(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        .where(PortfolioSectionModel.section_id == section_tag)
        .where(BlockModel.tag == block_tag)
    )

    return session.exec(statement).first()


def update_portfolio_block(
    session: Session,
    portfolio_id: int,
    section_tag: str,
    block_tag: str,
    **update_kwargs
) -> BlockModel:
    """
    Finds a specific block within a portfolio and section, applying user updates.
    This triggers the domain logic for conflict resolution if necessary.
    """

    block_model = get_portfolio_block_model(
        session, portfolio_id, section_tag, block_tag)

    if not block_model:
        raise KeyNotFoundError(
            f"Block '{block_tag}' not found in section '{section_tag}' "
            f"for portfolio {portfolio_id}"
        )

    domain_block = deserialize_block(block_model)

    domain_block.user_updates(**update_kwargs)

    updated_values = serialize_block(domain_block)

    block_model.current_content = updated_values.current_content
    block_model.last_user_edit_at = updated_values.last_user_edit_at
    block_model.in_conflict = updated_values.in_conflict
    block_model.conflict_content = updated_values.conflict_content

    session.add(block_model)
    return block_model


def get_portfolio_block(
    session: Session,
    portfolio_id: int,
    section_tag: str,
    block_tag: str
) -> Block | None:
    """
    Retrieves a single Block domain object by traversing the Portfolio
    and Section hierarchy.
    """

    block_model = get_portfolio_block_model(
        session, portfolio_id, section_tag, block_tag)

    if not block_model:
        return None

    return deserialize_block(block_model)


def sync_domain_block_to_db(
    session: Session,
    portfolio_id: int,
    section_tag: str,
    block_tag: str,
    domain_block: Block
) -> BlockModel:
    """
    Takes a modified Domain Block and persists its state to the database
    for a specific portfolio and section.
    """

    # 1. Locate the existing database record
    statement = (
        select(BlockModel)
        .join(PortfolioSectionModel)
        .join(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        .where(PortfolioSectionModel.section_id == section_tag)
        .where(BlockModel.tag == block_tag)
    )

    block_model = session.exec(statement).first()

    if not block_model:
        raise KeyNotFoundError(
            f"Block '{block_tag}' not found in section '{section_tag}' "
            f"for portfolio {portfolio_id}"
        )

    updated_values = serialize_block(domain_block)

    # Update the block model to reflect the new information in the domain
    block_model.current_content = updated_values.current_content
    block_model.conflict_content = updated_values.conflict_content
    block_model.in_conflict = updated_values.in_conflict
    block_model.last_generated_at = updated_values.last_generated_at
    block_model.last_user_edit_at = updated_values.last_user_edit_at

    session.add(block_model)

    return block_model


def get_project_card_model(
    session: Session,
    portfolio_id: int,
    project_name: str,
) -> Optional[PortfolioProjectCardModel]:
    """Retrieve a single project card for a specific portfolio and project."""
    statement = (
        select(PortfolioProjectCardModel)
        .where(PortfolioProjectCardModel.portfolio_id == portfolio_id)
        .where(PortfolioProjectCardModel.project_name == project_name)
    )
    return session.exec(statement).first()


def get_project_cards_for_portfolio(
    session: Session,
    portfolio_id: int,
    themes: Optional[list[str]] = None,
    tones: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    skills: Optional[list[str]] = None,
) -> list[PortfolioProjectCardModel]:
    """
    Retrieve all project cards for a portfolio, with optional filtering.
    Filtering is done in Python since SQLite JSON array querying is unreliable.
    Showcase cards are returned first, then alphabetically by project name.
    """
    statement = (
        select(PortfolioProjectCardModel)
        .where(PortfolioProjectCardModel.portfolio_id == portfolio_id)
    )
    cards = list(session.exec(statement).all())

    if themes:
        theme_set = {t.lower() for t in themes}
        cards = [c for c in cards if any(
            t.lower() in theme_set for t in (c.themes or []))]

    if tones:
        tone_set = {t.lower() for t in tones}
        cards = [c for c in cards if c.tones and c.tones.lower() in tone_set]

    if tags:
        # Check user tags_override first, fall back to auto tags
        tag_set = {t.lower() for t in tags}
        cards = [c for c in cards if any(
            t.lower() in tag_set
            for t in (c.tags_override if c.tags_override is not None else (c.tags or []))
        )]

    if skills:
        skill_set = {s.lower() for s in skills}
        cards = [c for c in cards if any(
            s.lower() in skill_set for s in (c.skills or []))]

    # Showcase cards float to the top
    cards.sort(key=lambda c: (not c.is_showcase, c.project_name))
    return cards


def update_portfolio_from_domain(session: Session, portfolio_id: int, domain_portfolio: Portfolio) -> PortfolioModel:
    """
    Syncs a domain Portfolio object back to the database.
    Handles updating existing sections/blocks and adding new ones.
    Also merges project_cards: refreshes auto-populated fields, preserves user overrides
    and the is_showcase flag.
    """

    # Fetch the existing model with its relationships
    statement = (
        select(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        .options(
            joinedload(PortfolioModel.sections)  # type: ignore
            .joinedload(PortfolioSectionModel.blocks),  # type: ignore
            joinedload(PortfolioModel.project_cards),  # type: ignore
        )
    )

    portfolio_model = session.exec(statement).unique().first()

    if not portfolio_model:
        raise KeyNotFoundError(f"Portfolio {portfolio_id} not found")

    # Update Portfolio-level metadata
    portfolio_model.last_updated_at = domain_portfolio.metadata.last_updated_at
    portfolio_model.title = domain_portfolio.title

    # Sync Sections
    existing_sections_map = {s.section_id: s for s in portfolio_model.sections}

    for domain_section in domain_portfolio.sections:
        if domain_section.id in existing_sections_map:
            # Update existing section
            section_model = existing_sections_map[domain_section.id]
            sync_section_blocks(session, section_model, domain_section)
        else:
            # This is a brand new section generated by the system
            new_section_model = serialize_portfolio_section(domain_section)
            new_section_model.portfolio_id = portfolio_model.id
            session.add(new_section_model)

    # Sync project cards
    existing_cards_map = {c.project_name: c for c in portfolio_model.project_cards}

    for domain_card in (domain_portfolio.project_cards or []):
        if domain_card.project_name in existing_cards_map:
            card_model = existing_cards_map[domain_card.project_name]
            # Always refresh auto-populated fields
            card_model.image_data = domain_card.image_data
            card_model.summary = domain_card.summary
            card_model.themes = list(domain_card.themes)
            card_model.tones = domain_card.tones
            card_model.tags = list(domain_card.tags)
            card_model.skills = list(domain_card.skills)
            card_model.frameworks = list(domain_card.frameworks)
            card_model.languages = dict(domain_card.languages)
            card_model.start_date = domain_card.start_date
            card_model.end_date = domain_card.end_date
            card_model.is_group_project = domain_card.is_group_project
            card_model.collaboration_role = domain_card.collaboration_role
            card_model.work_pattern = domain_card.work_pattern
            card_model.commit_type_distribution = dict(domain_card.commit_type_distribution)
            card_model.activity_metrics = dict(domain_card.activity_metrics)
            # Preserve is_showcase (user-controlled), title_override, summary_override,
            # tags_override, and last_user_edit_at — never overwrite these on refresh
            session.add(card_model)
        else:
            # New project added to the portfolio
            new_card_model = serialize_project_card(domain_card, portfolio_id)
            session.add(new_card_model)

    return portfolio_model


def sync_section_blocks(session: Session, section_model: PortfolioSectionModel, domain_section: PortfolioSection):
    """Updates the blocks within a specific section model based on domain state."""
    existing_blocks_map = {b.tag: b for b in section_model.blocks}

    for tag in domain_section.block_order:
        domain_block = domain_section.blocks_by_tag[tag]
        serialized_block = serialize_block(domain_block)

        if tag in existing_blocks_map:
            block_model = existing_blocks_map[tag]
            # Update the fields that change during a merge/conflict
            block_model.current_content = serialized_block.current_content
            block_model.conflict_content = serialized_block.conflict_content
            block_model.in_conflict = serialized_block.in_conflict
            block_model.last_generated_at = serialized_block.last_generated_at
        else:
            # Add new block found in the merged domain object
            serialized_block.section_id = section_model.id
            session.add(serialized_block)
