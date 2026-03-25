"""
Generation service for a portfolio.
"""
from typing import Optional
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload

from src.core.report import UserReport
from src.core.portfolio.portfolio import Portfolio
from src.core.portfolio.cards.project_card import ProjectCard
from src.core.statistic import ProjectStatCollection
from src.utils.errors import KeyNotFoundError
from src.core.portfolio.portfolio import merge_portfolios
from src.database.api.CRUD.portfolio import update_portfolio_from_domain
from src.database import (
    get_project_report_by_name,
    get_project_report_models_by_names,
    get_engine,
    save_portfolio,
    load_portfolio,
    PortfolioModel,
    PortfolioSectionModel
)


def _build_project_cards(
    project_models: list,
    project_reports: list,
    top_n_showcase: int = 3,
) -> list[ProjectCard]:
    """
    Build one ProjectCard per project by extracting all relevant statistics.

    The top_n_showcase projects (sorted by representation_rank) are automatically
    flagged as is_showcase=True. Users can change this later via the showcase endpoint.

    portfolio_id is set to -1 as a placeholder; it is assigned during save_portfolio
    after the PortfolioModel has been flushed and its PK is known.
    """
    from src.core.portfolio.project_summary import build_project_summary, configure_summary_run

    configure_summary_run(len(project_reports))

    # Determine default showcase set: top N by representation_rank
    ranked = sorted(
        zip(project_models, project_reports),
        key=lambda pair: (
            pair[0].representation_rank is None,
            pair[0].representation_rank if pair[0].representation_rank is not None else 10 ** 9,
            pair[0].created_at,
        ),
    )
    showcase_names = {pm.project_name for pm, _ in ranked[:top_n_showcase]}

    cards = []

    for model, report in zip(project_models, project_reports):
        if report is None:
            continue

        themes = report.get_value(ProjectStatCollection.PROJECT_THEMES.value) or []
        tones_raw = report.get_value(ProjectStatCollection.PROJECT_TONE.value)
        tones = str(tones_raw) if tones_raw else ""
        tags = report.get_value(ProjectStatCollection.PROJECT_TAGS.value) or []
        skills_raw = report.get_value(
            ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value) or []
        frameworks_raw = report.get_value(
            ProjectStatCollection.PROJECT_FRAMEWORKS.value) or []
        languages_raw = report.get_value(
            ProjectStatCollection.CODING_LANGUAGE_RATIO.value) or {}
        start_date = report.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = report.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        is_group = report.get_value(ProjectStatCollection.IS_GROUP_PROJECT.value) or False
        role = report.get_value(ProjectStatCollection.COLLABORATION_ROLE.value) or ""
        work_pattern = report.get_value(ProjectStatCollection.WORK_PATTERN.value) or ""
        commit_dist = report.get_value(
            ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value) or {}
        activity = report.get_value(ProjectStatCollection.ACTIVITY_METRICS.value) or {}

        summary = build_project_summary(report) or ""

        # Normalise skill/framework objects to plain strings
        skill_names = [getattr(s, "skill_name", str(s)) for s in skills_raw]
        framework_names = [getattr(f, "skill_name", str(f)) for f in frameworks_raw]
        # Normalise language keys
        language_dict = {str(k): float(v) for k, v in languages_raw.items()}

        cards.append(ProjectCard(
            portfolio_id=-1,  # placeholder; assigned after flush in save_portfolio
            project_name=model.project_name,
            image_data=model.image_data,
            summary=summary,
            themes=[str(t) for t in themes],
            tones=tones,
            tags=[str(t) for t in tags],
            skills=skill_names,
            frameworks=framework_names,
            languages=language_dict,
            start_date=start_date,
            end_date=end_date,
            is_group_project=bool(is_group),
            collaboration_role=str(role),
            work_pattern=str(work_pattern),
            commit_type_distribution=dict(commit_dist),
            activity_metrics=dict(activity),
            is_showcase=model.project_name in showcase_names,
        ))

    return cards


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

    Populates all three parts:
      Part A — ML-generated narrative sections (+ user-owned sections)
      Part B — is_showcase flag on the top-ranked project cards
      Part C — project cards with rich metadata from project statistics

    :param project_names: List of project names
    :type project_names: list[str]
    :param portfolio_title: Title of the portoflio
    :type portfolio_title: Optional[str]
    :return: Returns a portoflio model of what was saved
    :rtype: PortfolioModel
    """

    portfolio = _create_portfolio(project_names, portfolio_title)

    with Session(get_engine()) as session:
        project_models = get_project_report_models_by_names(session, project_names)
        project_reports = [
            get_project_report_by_name(session, name) for name in project_names
        ]

        portfolio.project_cards = _build_project_cards(project_models, project_reports)

        portfolio_model = save_portfolio(session, portfolio)
        session.commit()

        statement = (
            select(PortfolioModel)
            .where(PortfolioModel.id == portfolio_model.id)
            .options(
                joinedload(PortfolioModel.sections)  # type: ignore
                .joinedload(PortfolioSectionModel.blocks),  # type: ignore
                joinedload(PortfolioModel.project_cards),  # type: ignore
            )
        )

        fully_loaded_portfolio = session.exec(statement).unique().first()

    if fully_loaded_portfolio is None:
        raise Exception("Unkown exception was thrown while loading portoflio")

    return fully_loaded_portfolio


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

        # Regenerate Part A sections with updated information
        updated_portfolio = _create_portfolio(project_names, "")
        merged_portfolio = merge_portfolios(existing_portfolio, updated_portfolio)

        # Rebuild Part C cards from fresh statistics
        # (update_portfolio_from_domain preserves is_showcase and user overrides)
        project_models = get_project_report_models_by_names(session, project_names)
        project_reports = [
            get_project_report_by_name(session, name) for name in project_names
        ]
        merged_portfolio.project_cards = _build_project_cards(
            project_models, project_reports)

        portfolio_model = update_portfolio_from_domain(
            session, portfolio_id, merged_portfolio)
        session.commit()
        session.refresh(portfolio_model)

    return portfolio_model
