"""
This file will take the domain classes in our code base and turn
them into their respective SQLModels to be stored for future use
"""
from src.database.api.models import ResumeModel, ResumeItemModel
from typing import Optional

from src.core.report import FileReport, ProjectReport
from src.core.portfolio.portfolio import Portfolio, PortfolioSection
from src.core.portfolio.cards.project_card import ProjectCard
from src.core.resume.resume import Resume, ResumeItem
from src.database.api.models import (
    FileReportModel,
    ProjectReportModel,
    ResumeItemModel,
    ResumeModel,
    PortfolioModel,
    PortfolioSectionModel,
    BlockModel,
    PortfolioProjectCardModel,
)
from src.utils.errors import DomainClassToModelConverisonError
from src.core.portfolio.sections.block.block import Block, BlockContent


def serialize_file_report(file_report: FileReport) -> FileReportModel:
    """
    Serializes a FileReport domain object into a FileReportModel (SQLModel)
    Will error out if any of the attributes (like file_hash) are missing. This
    will commonly happen with tests.
    """

    project_name: str | None = file_report.project_name
    file_path: str | None = file_report.filepath
    file_hash: bytes | None = file_report.file_hash
    file_statistics: dict | None = file_report.statistics.to_json()
    is_info_file: bool | None = file_report.is_info_file

    if project_name is None:
        raise DomainClassToModelConverisonError(
            "project_name is None, cannot save FileReport")
    if file_path is None:
        raise DomainClassToModelConverisonError(
            "file_path is None, cannot save FileReport")
    if file_hash is None:
        raise DomainClassToModelConverisonError(
            "file_hash is None, cannot save FileReport")
    if file_statistics is None:
        raise DomainClassToModelConverisonError(
            "file_statistics is None, cannot save FileReport")
    if is_info_file is None:
        raise DomainClassToModelConverisonError(
            "is_info_file is None, cannot save FileReport")

    return FileReportModel(
        id=None,  # Auto Increment
        project_name=project_name,
        file_path=file_path,
        is_info_file=is_info_file,
        file_hash=file_hash,
        statistic=file_statistics
    )


def serialize_project_report(
    project_report: ProjectReport,
    user_config_id: Optional[int]
) -> ProjectReportModel:
    """
    Serializes a ProjectReport domain object into a ProjectReportModel (SQLModel)

    Args:
        project_report: Domain-level ProjectReport
        user_config_id: ID of the associated UserConfigModel

    Returns:
        ProjectReportModel ready to be added to the DB
    """

    project_name: str | None = project_report.project_name
    project_statistics: dict | None = project_report.project_statistics.to_json()

    if project_name is None:
        raise DomainClassToModelConverisonError(
            "project_name is None, cannot save ProjectReport")
    if project_statistics is None:
        raise DomainClassToModelConverisonError(
            "project_statistics is None, cannot save ProjectReport")

    project_model = ProjectReportModel(
        project_name=project_name,
        user_config_used=user_config_id,
        statistic=project_statistics,
        analyzed_count=1,
        parent=None
    )

    file_models = [serialize_file_report(fr)
                   for fr in project_report.file_reports]

    project_model.file_reports = file_models

    return project_model


def serialize_resume(resume: Resume) -> ResumeModel:
    return ResumeModel(
        id=None,
        email=resume.email,
        github=resume.github,
        skills=resume.skills,
        education=getattr(resume, "education", []) or [],
        awards=getattr(resume, "awards", []) or [],
    )


def serialize_resume_item(
    resume_item: ResumeItem,
    project_name: Optional[str] = None
) -> ResumeItemModel:

    if resume_item.title is None:
        raise DomainClassToModelConverisonError(
            "resume_item.title is None, cannot save ResumeItem")

    frameworks_json = []
    for fw in resume_item.frameworks:
        frameworks_json.append(str(fw.skill_name))

    return ResumeItemModel(
        id=None,
        project_name=project_name,
        title=resume_item.title,
        frameworks=frameworks_json,
        bullet_points=resume_item.bullet_points,
        start_date=resume_item.start_date,
        end_date=resume_item.end_date,
    )


def serialize_block(block: Block[BlockContent]) -> BlockModel:
    return BlockModel(
        tag=block.tag,
        content_type=block.current_content.content_type if block.current_content else "Unknown",
        last_generated_at=block.metadata.last_generated_at,
        last_user_edit_at=block.metadata.last_user_edit_at,
        in_conflict=block.metadata.in_conflict,
        current_content=block.current_content.raw_value() if block.current_content else None,
        conflict_content=block.metadata.conflict_content.raw_value(
        ) if block.metadata.conflict_content else None
    )


def serialize_portfolio_section(section: PortfolioSection) -> PortfolioSectionModel:
    section_model = PortfolioSectionModel(
        section_id=section.id,
        title=section.title,
        order=section.order,
        block_order=section.block_order
    )

    # Map the dictionary of blocks to a list of models
    section_model.blocks = [serialize_block(
        b) for b in section.blocks_by_tag.values()]
    return section_model


def serialize_project_card(card: ProjectCard, portfolio_id: int) -> PortfolioProjectCardModel:
    """
    Serializes a ProjectCard domain object into a PortfolioProjectCardModel.
    portfolio_id must be set (i.e. after the parent PortfolioModel has been flushed).
    """
    return PortfolioProjectCardModel(
        portfolio_id=portfolio_id,
        project_name=card.project_name,
        image_data=card.image_data,
        summary=card.summary,
        themes=list(card.themes),
        tones=card.tones,
        tags=list(card.tags),
        skills=list(card.skills),
        frameworks=list(card.frameworks),
        languages=dict(card.languages),
        start_date=card.start_date,
        end_date=card.end_date,
        is_group_project=card.is_group_project,
        collaboration_role=card.collaboration_role,
        work_pattern=card.work_pattern,
        commit_type_distribution=dict(card.commit_type_distribution),
        activity_metrics=dict(card.activity_metrics),
        is_showcase=card.is_showcase,
        title_override=card.title_override,
        summary_override=card.summary_override,
        tags_override=list(card.tags_override) if card.tags_override is not None else None,
        last_user_edit_at=card.last_user_edit_at,
    )


def serialize_portfolio(portfolio: Portfolio) -> PortfolioModel:
    portfolio_model = PortfolioModel(
        title=portfolio.title,
        creation_time=portfolio.metadata.creation_time,
        last_updated_at=portfolio.metadata.last_updated_at,
        project_ids_include=portfolio.metadata.project_ids_include,
        mode=portfolio.metadata.mode,
    )

    portfolio_model.sections = [
        serialize_portfolio_section(s) for s in portfolio.sections]

    # project_cards are written separately in save_portfolio after flush
    # (portfolio_id is not known until after session.flush())

    return portfolio_model
