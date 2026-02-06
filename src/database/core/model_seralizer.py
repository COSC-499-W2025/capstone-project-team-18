"""
This file will take the domain classes in our code base and turn
them into their respective SQLModels to be stored for future use
"""
from src.database.api.models import ResumeModel, ResumeItemModel
from typing import Optional

from src.core.report import FileReport, ProjectReport
from src.core.resume.resume import Resume, ResumeItem
from src.database.api.models import FileReportModel, ProjectReportModel, ResumeItemModel, ResumeModel
from src.utils.errors import DomainClassToModelConverisonError


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

    return ProjectReportModel(
        project_name=project_name,
        user_config_used=user_config_id,
        statistic=project_statistics
    )


def serialize_resume(resume: Resume) -> ResumeModel:
    return ResumeModel(
        id=None,
        email=resume.email,
        github=resume.github,
        skills=resume.skills,
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
