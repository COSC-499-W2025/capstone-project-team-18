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
