from src.core.portfolio.sections.block.block import Block
from src.database.core.model_serializer import serialize_block
from src.database.core.model_deserializer import deserialize_block
from src.database.api.models import PortfolioModel, PortfolioSectionModel, BlockModel
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from src.database.api.models import PortfolioModel, PortfolioSectionModel
from src.core.portfolio.portfolio import Portfolio
from src.database.core.model_serializer import serialize_portfolio
from src.database.core.model_deserializer import deserialize_portfolio


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
        raise ValueError(
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

    statement = (
        select(BlockModel)
        .join(PortfolioSectionModel)
        .join(PortfolioModel)
        .where(PortfolioModel.id == portfolio_id)
        # PortfolioSectionModel.section_id is the string tag (e.g., 'intro_1')
        .where(PortfolioSectionModel.section_id == section_tag)
        # BlockModel.tag is the unique string tag within that section
        .where(BlockModel.tag == block_tag)
    )

    block_model = session.exec(statement).first()

    if not block_model:
        return None

    return deserialize_block(block_model)
