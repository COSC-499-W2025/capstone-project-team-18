"""
This file holds the main service, the miner.
"""

from typing import Optional, Callable
from dataclasses import dataclass
import tempfile
import time
from sqlalchemy.orm import Session

from src.utils.pathing_utils import unzip_file_bytes
from src.core.project_discovery.project_discovery import discover_projects, ProjectLayout
from src.core.analyzer import extract_file_reports
from src.core.report import ProjectReport
from src.infrastructure.database.base import Base, get_engine
from src.infrastructure.database.utils.database_modify import create_row
from src.infrastructure.log.logging import get_logger
from src.infrastructure.database.utils.database_access import get_user_config
from src.services.preferences.preference_service import UserConfig
from src.utils.errors import NoDiscoveredProjects, MissingStartMinerConsent

logger = get_logger(__name__)


@dataclass
class MinerResults():
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

    return ProjectReport(
        project_name=project_layout.name,
        project_path=project_layout.root_path,
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
        for pr in project_report:

            # Save File Reports
            file_report_rows = []
            for fr in pr.file_reports:
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
    user_report_title: str = f"UserReport{str(int(time.time()))}",

    github: Optional[str] = None,
    email: Optional[str] = None,
    language_filter: Optional[list[str]] = None,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,

) -> MinerResults:
    """
    This is the defacto function to start the minering function
    for the Artifact Miner. This function receives the bytes and file
    format of the zipped file (.zip, .7z, etc). There is no output of this
    function, but rather the miner results are written to the database for
    later retrieval.

    :param zipped_bytes: The bytes of a zipped file.
    :type zipped_bytes: bytes
    :param zipped_format: The file format of the file (".7z", ".zip", etc)
    :type zipped_format: str
    :param user_report_title: The user report name you would like to save in the database
    :type user_report_title: str
    :param email: The git email of the user
    :type email: Optional[str]
    :param language_filter: A list of strings of what file formats to ignore
    :type language_filter: Optional[list[str]]
    :param progress_callback: Used by the CLI to make a visual progress bar.
    :type progress_callback: Optional[Callable[[str, int, int, str], None]]
    :return: Returns a MinerResults object
    :rtype: MinerResults
    """

    logger.info("Starting analysis for the zipped file")

    user_config = get_user_config()

    if user_config is None:
        user_config = UserConfig(
            consent=True,
            github=github,
            email=email,
            language_filter=language_filter
        )

    if not user_config.consent:
        raise MissingStartMinerConsent()

    projects_discovered = _discover_projects_from_file(
        zipped_bytes, zipped_format)

    project_reports = [_analyze_project_files(
        layout, user_config) for layout in projects_discovered]

    if project_reports == []:
        raise NoDiscoveredProjects(
            "The analyzer found no projects to analyze. "
            "Please check your zipped file. "
            "If configured, check your git email."
            "The analyzer will not analyze Git projects you have not contributed to."
        )

    _save_project_report_to_db(project_reports)

    return MinerResults(True)
