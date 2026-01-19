"""
This file holds the main service, the miner.
"""

from typing import Optional, Callable
from dataclasses import dataclass
import tempfile
import time
from sqlalchemy.orm import Session

from src.utils.pathing_utils import unzip_file_bytes
from src.utils.project_discovery.project_discovery import discover_projects
from src.classes.analyzer import extract_file_reports
from src.classes.report import ProjectReport, UserReport
from src.database.base import get_engine, Base
from src.database.utils.database_modify import create_row
from src.utils.log.logging import get_logger
from src.utils.errors import NoDiscoveredProjects

logger = get_logger(__name__)


@dataclass
class MinerResults():
    user_report: UserReport
    success: bool


def start_miner_service(
    zipped_bytes: bytes,
    zipped_format: str,
    user_report_title: str = f"UserReport{str(int(time.time()))}",

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

    # TODO: Retrieve preferences from the database and validate parameters (like consent)

    # Unzip the file into temp directory
    unzipped_dir = tempfile.mkdtemp(prefix="artifact_miner_")
    unzip_file_bytes(zipped_bytes, zipped_format, unzipped_dir)

    # Project Discovery
    project_list = discover_projects(unzipped_dir)

    logger.debug(project_list)

    # Initialize progress bar with total project count
    if progress_callback:
        progress_callback("start", 0, len(project_list), "")
        progress_callback("unzip", 1, 1, "")
        progress_callback("discovery", 1, 1, "")

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
                project, email, language_filter)  # get the project's FileReports

            logger.debug(
                "File reports for project %s file_reports", project.name)

            if file_reports == []:
                continue  # skip if directory is empty

            # create the rows for the file reports FOR THIS PROJECT ONLY
            file_report_rows = []  # Reset for each project
            for fr in file_reports:
                file_report = create_row(fr)
                file_report_rows.append(file_report)

            # make a ProjectReport with the FileReports
            project_report = ProjectReport(
                project_name=project.name,
                project_path=project.root_path,
                project_repo=project.repo,
                file_reports=file_reports,
                user_email=email
            )
            # store ProjectReports for UserReport
            project_reports.append(project_report)
            # create project_report row and configure FK relations
            project_row = create_row(report=project_report)
            project_row.file_reports.extend(file_report_rows)  # type: ignore
            project_report_rows.append(project_row)

        if project_reports == []:
            raise NoDiscoveredProjects(
                "The analyzer found no projects to analyze. "
                "Please check your zipped file. "
                "If configured, check your git email."
                "The analyzer will not analyze Git projects you have not contributed to."
            )

        # Update at END of all project analysis
        if progress_callback:
            progress_callback("analysis", total_projects, total_projects, "")

        # =================== Saving stage ===================
        if progress_callback:
            progress_callback("saving", 1, 1, "")

        # make a UserReport with the ProjectReports
        user_report = UserReport(project_reports, user_report_title)

        # create a user_report row and configure FK relations
        user_row = create_row(report=user_report)
        user_row.project_reports.extend(project_report_rows)  # type: ignore

        # Insert all of the rows into the database (INSIDE the session block)
        session.add_all([user_row])  # type: ignore
        session.commit()

        # =================== Analysis Complete ===================
        if progress_callback:
            progress_callback("complete", 1, 1, "")

    return MinerResults(user_report, True)
