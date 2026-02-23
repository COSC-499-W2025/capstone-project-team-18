"""
Generation service for a portfolio.
"""
from typing import Optional
from sqlmodel import Session

from src.core.report import UserReport
from src.core.portfolio.portfolio import Portfolio
from src.utils.errors import KeyNotFoundError
from src.core.portfolio.portfolio import merge_portfolios
from src.database.api.CRUD.portfolio import update_portfolio_from_domain
from src.database import (
    get_project_report_by_name,
    get_engine,
    save_portfolio,
    load_portfolio,
    PortfolioModel
)


def _create_portfolio(project_names: list[str], portfolio_title: Optional[str]) -> Portfolio:
    """
    Create a brand new portoflio object with the provided projects and with
    the passed in title. This portfolio will have all deafult, system, sections
    with the most up to date information

    :param project_names: List of all project names to include in the resulting portoflio
    :type project_names: list[str]
    :param portfolio_title: The title of the portfolio. Will deafult if not provided.
    :type portfolio_title: Optional[str]
    """

    prs = []

    with Session(get_engine()) as session:
        for pid in project_names:
            pr = get_project_report_by_name(session, pid)
            if pr is None:
                raise KeyNotFoundError(f"No project report with key {pid}")
            prs.append(pr)

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

    :param project_names: List of project names
    :type project_names: list[str]
    :param portfolio_title: Title of the portoflio
    :type portfolio_title: Optional[str]
    :return: Returns a portoflio model of what was saved
    :rtype: PortfolioModel
    """

    portfolio = _create_portfolio(project_names, portfolio_title)

    with Session(get_engine()) as session:
        portfolio_model = save_portfolio(session, portfolio)
        session.commit()
        session.refresh(portfolio_model)

    return portfolio_model


def update_portfolio(portfolio_id: int) -> PortfolioModel:
    """
    Updates/Refreshes a portfolio with the most current project information
    blocks will enter conflict mode if user changes conflict with
    the system changes

    :param portfolio_id: The Id of the portfolio to referesh
    :type portfolio_id: int
    :raises KeyNotFoundError: Can't find the specific portoflio id
    :return: A model of the updated portoflio.
    :rtype: PortfolioModel
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

        portfolio_model = update_portfolio_from_domain(
            session, portfolio_id, merged_portfolio)
        session.commit()
        session.refresh(portfolio_model)

    return portfolio_model
