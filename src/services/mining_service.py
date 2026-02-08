"""
This file holds the main service, the miner.
"""

import tempfile
from sqlalchemy.orm import Session
from dataclasses import dataclass
from pydantic import BaseModel

from src.utils.pathing_utils import unzip_file_bytes
from src.core.project_discovery.project_discovery import discover_projects, ProjectLayout
from src.core.analyzer import extract_file_reports
from src.core.report import ProjectReport
from src.database.base import get_engine, Base
from src.database.utils.database_modify import create_row
from src.infrastructure.log.logging import get_logger
from src.services.preferences.preference_service import UserConfig
from src.utils.errors import (
    NoDiscoveredProjects,
    MissingStartMinerConsent,
    NoRevelantFiles,
    ErrorCode,
    ArtifactMinerException
)

logger = get_logger(__name__)


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

    file_reports = extract_file_reports(
        project_file=project_layout,
        email=user_config.email,
        github=user_config.github,
        language_filter=user_config.language_filter
    )

    logger.debug("File reports for project %s file_reports",
                 project_layout.name)

    if file_reports == []:
        logger.warning(f"{project_layout.name} had no FileReports")
        raise NoRevelantFiles(
            "f{project_layout.name} had no revelent files to analyze")

    return ProjectReport(
        project_name=project_layout.name,
        project_path=str(project_layout.root_path),
        project_repo=project_layout.repo,
        file_reports=file_reports,
        user_email=user_config.email,
        user_github=user_config.github
    )


def _save_project_report_to_db(project_report: list[ProjectReport]) -> None:
    """
    Saves many ProjectReports and their corresponding FileReports
    to the database.

    :param project_report: ProjectReport(s) to be saved
    :type project_report: list[ProjectReport]
    """

    engine = get_engine()

    # Create tables if they do not exist
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # For each project, extract file reports and create ProjectReports
        project_reports = []  # Stores ProjectReport objs
        project_report_rows = []  # Stores ProjectReportTable objs

        total_projects = len(project_list)

        # =================== Analysis Stage ===================
        for idx, project in enumerate(project_list):
            # Update at START of processing each project (idx is 0-based, so idx is the "current" count)
            if progress_callback:
                progress_callback(
                    "analysis", idx, total_projects, project.name)

            file_reports = extract_file_reports(
                project, email, github, language_filter)  # get the project's FileReports

            logger.debug(
                "File reports for project %s file_reports", project.name)

            if file_reports == []:
                continue  # skip if directory is empty

            # create the rows for the file reports FOR THIS PROJECT ONLY
            file_report_rows = []  # Reset for each project
            for fr in file_reports:
                fr.filepath = f"{project.name}/{fr.filepath}"
                file_report = create_row(fr)
                file_report_rows.append(file_report)

            # Create project_report row and configure FK relations
            project_row = create_row(pr)
            project_row.file_reports.extend(file_report_rows)

            # Insert all of the rows into the database
            session.add_all([project_row])
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

    _save_project_report_to_db(project_reports)

    success = len(project_errors) == 0
    return MinerResults(project_errors=project_errors,
                        success=success,
                        project_reports=project_reports)
