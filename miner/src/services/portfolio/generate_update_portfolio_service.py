"""
Generation service for a portfolio.
"""
from typing import Optional
from sqlmodel import Session

from src.core.report import UserReport
from src.core.portfolio.portfolio import Portfolio
from src.utils.errors import KeyNotFoundError
from src.core.portfolio.portfolio import merge_portfolios
from src.database import (
    get_project_report_by_name,
    get_engine,
    save_portfolio,
    load_portfolio,
    PortfolioModel
)


def _create_portfolio(project_names: list[str], portfolio_title: Optional[str]) -> Portfolio:
    """
    Create a new portfolio objects with the provided project names and title.
    A new portfolio will be generated with the most up to date project information.
    """

    prs = []

    with Session(get_engine()) as session:
        for pid in project_names:
            prs.append(get_project_report_by_name(session, pid))

    portfolio = UserReport(project_reports=prs,
                           report_name="").generate_portfolio()

    if portfolio_title:
        portfolio.title = portfolio_title

    portfolio.metadata.project_ids_include = project_names

    return portfolio


def generate_and_save_portfolio(project_names: list[str], portfolio_title: Optional[str]) -> PortfolioModel:
    """
    This service will generate a brand new portfolio based on the project_ids
    passed. The portfolio will be given the title passed in, or it will default
    to a placeholder title.
    """

    portfolio = _create_portfolio(project_names, portfolio_title)

    with Session(get_engine()) as session:
        portfolio_model = save_portfolio(session, portfolio)
        session.commit()
        session.refresh(portfolio_model)

    return portfolio_model


def update_portfolio(portfolio_id: int) -> PortfolioModel:
    """
    Updates a portfolio with the most current project information
    blocks will enter conflict mode if user changes conflict with
    the system changes
    """
    portfolio_model = None

    with Session(get_engine()) as session:
        existing_portfolio = load_portfolio(session, portfolio_id)

        if existing_portfolio is None:
            raise KeyNotFoundError(
                f"No portfolio in DB with key {portfolio_id}")

        project_names = existing_portfolio.metadata.project_ids_include

        # Regenerate the portfolio with new information
        updated_portfolio = _create_portfolio(project_names, "")

        merged_portfolio = merge_portfolios(
            existing_portfolio, updated_portfolio)

        portfolio_model = save_portfolio(session, merged_portfolio)
        session.commit()
        session.refresh(portfolio_model)

    return portfolio_model
