"""
This file is the starting script for the application.
It provides logic for the CLI that the user will
interact with to begin the artifact miner.
- To start the CLI tool, run this file.
"""

from utils.zipped_utils import unzip_file
from utils.project_discovery import discover_projects
from classes.analyzer import extract_file_reports
from classes.report import ProjectReport, UserReport
from classes.cli import ArtifactMiner
import tempfile


def start_miner(zipped_file: str) -> None:
    """
    This function defines the main application
    logic for the Artifact Miner. Currently,
    results are printed to the terminal

    Args:
        - zipped_file : str The filepath to the zipped file.
    """

    # Unzip the zipped file into temporary directory
    unzipped_dir = tempfile.mkdtemp(prefix="artifact_miner_")
    unzip_file(zipped_file, unzipped_dir)

    project_list = discover_projects(unzipped_dir)

    # For each project, extract file reports and create ProjectReports
    project_reports = []
    for project in project_list:
        file_reports = extract_file_reports(project)

        pr = ProjectReport(
            project_name=project.name,
            file_reports=file_reports
        )

        project_reports.append(pr)

    user_report = UserReport(project_reports)

    # TODO: Add User Report Processing


if __name__ == '__main__':
    start_miner(
        "/workspaces/capstone-project-team-18/tests/resources/mac_projects.zip")
    ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference
