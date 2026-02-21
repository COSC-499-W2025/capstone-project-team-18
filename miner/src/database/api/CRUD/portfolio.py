from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from typing import Optional

from src.core.portfolio.sections.block.block import Block
from src.database.core.model_serializer import serialize_block
from src.database.core.model_deserializer import deserialize_block
from src.database.api.models import PortfolioModel, PortfolioSectionModel, BlockModel
from src.core.portfolio.portfolio import Portfolio, PortfolioSection
from src.database.core.model_serializer import serialize_portfolio, serialize_portfolio_section
from src.database.core.model_deserializer import deserialize_portfolio
from src.utils.errors import KeyNotFoundError


def save_portfolio(session: Session, portfolio: Portfolio) -> PortfolioModel:
    """
    Saves a portfolio to the database. Assumes this portfolio is a new portfolio,
    and is not updating a new portfolio.
    """

    portfolio_model = serialize_portfolio(portfolio)
    session.add(portfolio_model)

    return portfolio_model


def load_portfolio(session: Session, portfolio_id: int) -> Portfolio | None:
    """
    Retrieves the portfolio for a specific user and converts it back
    into a Domain Portfolio object.

    Uses joinedload to fetch Sections and Blocks in a single hit.
    """

    # We use joinedload to prevent N+1 query problems
    # This fetches Portfolio -> Sections -> Blocks in one go
    statement = (
        select(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        .options(
            joinedload(PortfolioModel.sections)  # pyright: ignore
            .joinedload(PortfolioSectionModel.blocks)  # pyright: ignore
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


def update_portfolio_from_domain(session: Session, portfolio_id: int, domain_portfolio: Portfolio) -> PortfolioModel:
    """
    Syncs a domain Portfolio object back to the database.
    Handles updating existing sections/blocks and adding new ones.
    """

    # Fetch the existing model with its relationships
    statement = (
        select(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        .options(joinedload(PortfolioModel.sections)  # type: ignore
                 .joinedload(PortfolioSectionModel.blocks))  # type: ignore
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
            new_section_model = serialize_portfolio_section(
                domain_section)  # Assuming you have this
            new_section_model.portfolio_id = portfolio_model.id
            session.add(new_section_model)

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
