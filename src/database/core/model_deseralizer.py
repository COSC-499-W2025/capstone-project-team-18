"""
This file will take the models from the database and load
them into domain classes
"""

from src.core.report import FileReport, ProjectReport
from src.core.statistic import StatisticIndex, FileStatCollection, ProjectStatCollection, deserialize, Statistic
from src.database.api.models import FileReportModel, ProjectReportModel
from src.infrastructure.log.logging import get_logger

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


def deseralize_file_report(file_report_model: FileReportModel) -> FileReport:
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


def deseralize_project_report(project_report_model: ProjectReportModel) -> ProjectReport:
    """
    Turn a ProjectReportModel into a ProjectReport domain object.
    """
    # Convert the serialized statistics JSON into a StatisticIndex
    stat_index = deserialize_statistics(project_report_model.statistic)

    # Deserialize file reports if needed
    file_reports = [
        deseralize_file_report(f) for f in project_report_model.file_reports
    ] if project_report_model.file_reports else []

    return ProjectReport(
        project_name=project_report_model.project_name,
        statistics=stat_index,
        file_reports=file_reports,
    )
