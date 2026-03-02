"""
This file holds the main service, the miner.
"""

import tempfile
from numbers import Number
from typing import Optional
from sqlmodel import SQLModel, Session
from dataclasses import dataclass
from pydantic import BaseModel

from src.utils.pathing_utils import unzip_file_bytes
from src.core.project_discovery.project_discovery import discover_projects, ProjectLayout
from src.core.analyzer import extract_file_reports
from src.core.report import ProjectReport
from src.core.statistic import Statistic, ProjectStatCollection
from src.database.core.base import get_engine
from src.database.api.CRUD.projects import get_latest_related_project_report, save_project_report
from src.infrastructure.log.logging import get_logger
from src.database.api.models import UserConfigModel as UserConfig
from src.utils.errors import (
    NoDiscoveredProjects,
    MissingStartMinerConsent,
    NoRevelantFiles,
    ErrorCode,
    ArtifactMinerException
)

logger = get_logger(__name__)


def _is_number(value: object) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _safe_key_name(value: object) -> str:
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value)


def _collect_numeric_differences(
    key_prefix: str,
    current_value: object,
    previous_value: object,
    deltas: dict[str, float],
) -> None:
    if _is_number(current_value):
        previous_number = previous_value if _is_number(previous_value) else 0
        difference = float(current_value) - float(previous_number)
        if difference != 0:
            deltas[key_prefix] = difference
        return

    if isinstance(current_value, dict):
        previous_dict = previous_value if isinstance(
            previous_value, dict) else {}
        keys = set(current_value.keys()) | set(previous_dict.keys())

        for key in keys:
            key_name = _safe_key_name(key)
            nested_prefix = f"{key_prefix}.{key_name}"
            _collect_numeric_differences(
                nested_prefix,
                current_value.get(key),
                previous_dict.get(key),
                deltas,
            )


def _compute_project_statistics_deltas(
    current_report: ProjectReport,
    previous_report: ProjectReport,
) -> dict[str, float]:
    previous_stats_by_name = {
        statistic.get_template().name: statistic.value
        for statistic in previous_report.project_statistics
    }

    deltas: dict[str, float] = {}
    for statistic in current_report.project_statistics:
        stat_name = statistic.get_template().name
        _collect_numeric_differences(
            stat_name,
            statistic.value,
            previous_stats_by_name.get(stat_name),
            deltas,
        )

    return deltas


class ProjectError(BaseModel):
    """Represents a single project-level error"""
    project_name: str
    error_code: str
    error_message: str


@dataclass
class MinerResults():
    """Results from the mining operation"""
    project_errors: list[ProjectError]
    project_reports: list[ProjectReport]
    success: bool


def _discover_projects_from_file(
    zipped_bytes: bytes,
    zipped_format: str
) -> list[ProjectLayout]:
    """
    Unzips the files form a user uploaded zip
    into a temporary a directory, and discover projects.

    :param zipped_bytes: The bytes of the zipped file
    :param zipped_format: The file format of the file (".7z", ".zip", etc)
    :return: List of projects described in the zipped file.
    :rtype: ProjectLayout
    """

    # Unzip the file into temp directory
    unzipped_dir = tempfile.mkdtemp(prefix="artifact_miner_")
    unzip_file_bytes(zipped_bytes, zipped_format, unzipped_dir)

    # Project Discovery
    project_list = discover_projects(unzipped_dir)

    logger.debug(f"Project Discovery: {project_list}")

    return project_list


def _analyze_project_files(
    project_layout: ProjectLayout,
    user_config: UserConfig,
) -> ProjectReport:
    """
    Takes a defined ProjectLayout and returns a
    full ProjectReport. Note, if a ProjectReport
    has no FileReports, that PR is still returned,
    just as an empty ProjectReport.

    :param project_layout: The layout of the project to be analyzed.
    :type project_files: ProjectLayout
    :param user_config: The configuations of the user
    :type user_config: UserConfig
    :return: A ProjectReport based on the ProjectLayout
    :rtype: Optional[ProjectReport]
    """

    file_reports, needs_recomputation = extract_file_reports(
        project_file=project_layout,
        user_config=user_config
    )

    logger.debug("File reports for project %s file_reports",
                 project_layout.name)

    if file_reports == []:
        logger.warning(f"{project_layout.name} had no FileReports")
        raise NoRevelantFiles(
            "f{project_layout.name} had no revelent files to analyze")

    engine = get_engine()

    with Session(engine) as session:
        previous_report = get_latest_related_project_report(
            session,
            project_layout.name,
        )

    if needs_recomputation:
        project_report = ProjectReport(
            project_name=project_layout.name,
            project_path=str(project_layout.root_path),
            project_repo=project_layout.repo,
            file_reports=file_reports,
            user_email=user_config.user_email,
            user_github=user_config.github
        )

        if previous_report is not None:
            project_report.project_statistics.add(
                Statistic(
                    ProjectStatCollection.PREVIOUS_ANALYSIS_PROJECT.value,
                    previous_report.project_name,
                )
            )

            deltas = _compute_project_statistics_deltas(
                project_report,
                previous_report,
            )

            if deltas:
                project_report.project_statistics.add(
                    Statistic(
                        ProjectStatCollection.PROJECT_STATISTICS_DELTA.value,
                        deltas,
                    )
                )

        return project_report
    else:
        project_report = ProjectReport(
            project_name=project_layout.name,
            project_path=str(project_layout.root_path),
            project_repo=project_layout.repo,
            file_reports=file_reports,
            user_email=user_config.user_email,
            user_github=user_config.github
        )

        return project_report


def _save_project_report_to_db(project_report: list[ProjectReport], user_config_id: Optional[int]) -> None:
    """
    Saves many ProjectReports and their corresponding FileReports
    to the database.

    :param project_report: ProjectReport(s) to be saved
    :type project_report: list[ProjectReport]
    """

    engine = get_engine()

    # Create tables if they do not exist
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for pr in project_report:
            save_project_report(session, pr, user_config_id)
            session.commit()


def start_miner_service(
    zipped_bytes: bytes,
    zipped_format: str,
    user_config: UserConfig
) -> MinerResults:
    """
    This is the defacto function to start the miner function
    for the Artifact Miner. This function receives the bytes and file
    format of the zipped file (.zip, .7z, etc). Discovered projects are
    analyzed individually, and errors are caught per-project to allow
    processing to continue. ProjectReports and their corrsponding FileReports
    are written to the local database.

    Per-project errors are NOT raised but collected in MinerResults.project_errors:
        - NO_RELEVANT_FILES: Project has no analyzable files
        - NO_DISCOVERED_PROJECTS: No projects found in discovery (caught per-project)
        - ANALYSIS_FAILED: Analysis operation failed
        - UNKNOWN_ERROR: Unexpected exception during analysis

    :param zipped_bytes: The bytes of a zipped file.
    :type zipped_bytes: bytes
    :param zipped_format: The file format of the file (".7z", ".zip", etc)
    :type zipped_format: str
    :param user_config: The user's configuration
    :type user_config: UserConfig

    :return: Returns a MinerResults object containing analyzed projects and per-project errors
    :rtype: MinerResults

    :raises MissingStartMinerConsent: If user consent is not provided
    :raises NoDiscoveredProjects: If no projects are found in the zipped file

    """

    logger.info("Starting analysis for the zipped file")

    if not user_config.consent:
        raise MissingStartMinerConsent()

    projects_discovered = _discover_projects_from_file(
        zipped_bytes, zipped_format)

    if len(projects_discovered) == 0:
        raise NoDiscoveredProjects(
            "The analyzer found no projects to analyze.")

    # For every discovered project, try to analyze the project
    # If an error occurs, catch it for that project to be returned
    # and move on
    project_reports = []
    project_errors = []

    for layout in projects_discovered:
        try:
            report = _analyze_project_files(layout, user_config)
            project_reports.append(report)
        # we want to add a project error if no files are contributed to
            if report.contributed_to is False:
                logger.error(f"No user contribution in {layout.name}")
                project_errors.append(ProjectError(
                    project_name=layout.name,
                    error_code=ErrorCode.NO_RELEVANT_FILES.value,
                    error_message=f"No user contribution in {layout.name}"
                ))
        except ArtifactMinerException as e:
            logger.error(f"Error analyzing project {layout.name}: {e}")
            project_errors.append(ProjectError(
                project_name=layout.name,
                error_code=e.error_code.value,
                error_message=str(e)
            ))
        except Exception as e:
            logger.error(
                f"Unexpected error analyzing project {layout.name}: {e}")
            project_errors.append(ProjectError(
                project_name=layout.name,
                error_code=ErrorCode.UNKNOWN_ERROR.value,
                error_message=str(e)
            ))

    _save_project_report_to_db(project_reports, None)

    success = len(project_errors) == 0
    return MinerResults(project_errors=project_errors,
                        success=success,
                        project_reports=project_reports)
