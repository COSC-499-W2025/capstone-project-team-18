"""
This file will take the models from the database and load
them into domain classes
"""

import base64
from src.core.report import FileReport, ProjectReport
from src.core.resume.resume import Resume, ResumeItem
from src.database.api.models import FileReportModel, ProjectReportModel, ResumeItemModel, ResumeModel
from src.core.statistic import StatisticIndex, FileStatCollection, ProjectStatCollection, deserialize, Statistic, WeightedSkills
from src.infrastructure.log.logging import get_logger
from src.database.api.models import BlockModel
from src.core.portfolio.portfolio import Portfolio, PortfolioMetadata
from src.core.portfolio.sections.portfolio_section import PortfolioSection
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import (
    BlockContent,
    TextBlock,
    TextListBlock,
    BlockContentType
)
from src.core.portfolio.cards.project_card import ProjectCard
from src.database.api.models import PortfolioModel, PortfolioSectionModel, BlockModel, PortfolioProjectCardModel

logger = get_logger(__name__)

TEMPLATE_LOOKUP = {
    member.value.name: member.value
    for enum_cls in (ProjectStatCollection, FileStatCollection)
    for member in enum_cls
}


def deserialize_statistics(statistic: dict) -> StatisticIndex:
    """
    Convert a dict of serialized statistics back into a StatisticIndex.
    """
    stat_index = StatisticIndex()

    for key, value in statistic.items():
        template = TEMPLATE_LOOKUP.get(key)

        if template is None:
            logger.warning(
                f"Tried to desearlize statistics but couldn't find stat {key}")
            continue

        stat_value = deserialize(value)
        stat_index.add(Statistic(stat_template=template, value=stat_value))

    return stat_index


def deserialize_file_report(file_report_model: FileReportModel) -> FileReport:
    """
    Turn a FileReportModel into a FileReport object
    """

    stat_index = deserialize_statistics(file_report_model.statistic)

    return FileReport(
        statistics=stat_index,
        filepath=file_report_model.file_path,
        is_info_file=file_report_model.is_info_file,
        file_hash=file_report_model.file_hash,
        project_name=file_report_model.project_name
    )


def deserialize_project_report(project_report_model: ProjectReportModel) -> ProjectReport:
    """
    Turn a ProjectReportModel into a ProjectReport domain object.
    """
    # Convert the serialized statistics JSON into a StatisticIndex
    stat_index = deserialize_statistics(project_report_model.statistic)

    # Deserialize file reports if needed
    file_reports = [
        deserialize_file_report(f) for f in project_report_model.file_reports
    ] if project_report_model.file_reports else []

    return ProjectReport(
        project_name=project_report_model.project_name,
        statistics=stat_index,
        file_reports=file_reports,
    )


def deserialize_resume_item(
    model: ResumeItemModel
) -> ResumeItem:
    frameworks = [
        WeightedSkills(skill_name=fw, weight=1.0)
        for fw in model.frameworks
    ]

    return ResumeItem(
        title=model.title,
        frameworks=frameworks,
        bullet_points=model.bullet_points,
        start_date=model.start_date,
        end_date=model.end_date,
    )


def deserialize_resume(model: ResumeModel) -> Resume:
    resume = Resume(
        email=model.email,
        github=model.github,
        weight_skills=None,
        name=model.name,
        location=model.location,
        linkedin=model.linkedin,
        education=list(model.education or []),
        awards=list(model.awards or []),
    )

    # Restore skills list directly
    resume.skills = list(model.skills)

    if model.items:
        for item_model in model.items:
            resume.items.append(
                deserialize_resume_item(item_model)
            )

    return resume


def deserialize_block(model: BlockModel) -> Block:
    """
    Reconstructs a Block domain object from a BlockModel.
    Handles the conditional instantiation of BlockContent.
    """

    content: BlockContent | None = None
    if model.content_type == BlockContentType.TEXT:
        content = TextBlock(text=model.current_content)
    elif model.content_type == BlockContentType.TEXT_LIST:
        content = TextListBlock(items=model.current_content)

    block = Block(tag=model.tag, initial_content=content)

    block.metadata.last_generated_at = model.last_generated_at
    block.metadata.last_user_edit_at = model.last_user_edit_at
    block.metadata.in_conflict = model.in_conflict

    # 4. Restore Conflict Content if it exists
    if model.conflict_content is not None:
        if model.content_type == BlockContentType.TEXT:
            block.metadata.conflict_content = TextBlock(
                text=model.conflict_content)
        elif model.content_type == BlockContentType.TEXT_LIST:
            block.metadata.conflict_content = TextListBlock(
                items=model.conflict_content)

    return block


def deserialize_portfolio_section(model: PortfolioSectionModel) -> PortfolioSection:
    """
    Reconstructs a PortfolioSection domain object.
    Ensures that blocks are mapped back into the dictionary by their tags.
    """
    section = PortfolioSection(section_id=model.section_id, title=model.title)
    section.order = model.order

    deserialized_blocks = {
        b_model.tag: deserialize_block(b_model)
        for b_model in model.blocks
    }

    section.blocks_by_tag = deserialized_blocks
    section.block_order = model.block_order

    return section


def deserialize_project_card(model: PortfolioProjectCardModel) -> ProjectCard:
    """
    Reconstructs a ProjectCard domain object from a PortfolioProjectCardModel.
    """
    return ProjectCard(
        portfolio_id=model.portfolio_id,
        project_name=model.project_name,
        image_data=base64.b64encode(model.image_data).decode("utf-8") if model.image_data else None,
        summary=model.summary or "",
        themes=list(model.themes or []),
        tones=model.tones or "",
        tags=list(model.tags or []),
        skills=list(model.skills or []),
        frameworks=list(model.frameworks or []),
        languages=dict(model.languages or {}),
        start_date=model.start_date,
        end_date=model.end_date,
        is_group_project=bool(model.is_group_project),
        collaboration_role=model.collaboration_role or "",
        work_pattern=model.work_pattern or "",
        commit_type_distribution=dict(model.commit_type_distribution or {}),
        activity_metrics=dict(model.activity_metrics or {}),
        is_showcase=bool(model.is_showcase),
        title_override=model.title_override,
        summary_override=model.summary_override,
        tags_override=list(model.tags_override) if model.tags_override is not None else None,
        last_user_edit_at=model.last_user_edit_at,
    )


def deserialize_portfolio(model: PortfolioModel) -> Portfolio:
    """
    Reconstructs the full Portfolio domain tree.
    """

    sorted_section_models = sorted(model.sections, key=lambda x: x.order)
    sections = [deserialize_portfolio_section(
        s) for s in sorted_section_models]

    metadata = PortfolioMetadata(
        project_ids=model.project_ids_include,
        creation_date=model.creation_time,
        last_updated_at=model.last_updated_at,
    )

    portfolio = Portfolio(
        sections=sections, metadata=metadata, title=model.title)

    portfolio.project_cards = [
        deserialize_project_card(c) for c in (model.project_cards or [])
    ]

    return portfolio
