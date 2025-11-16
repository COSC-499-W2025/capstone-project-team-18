"""
This file is the starting script for the application.
It provides logic for the CLI that the user will
interact with to begin the artifact miner.
- To start the CLI tool, run this file.
"""

from typing import Optional
from utils.zipped_utils import unzip_file
from utils.project_discovery import discover_projects
from classes.analyzer import extract_file_reports
from classes.report import ProjectReport, UserReport
import tempfile


def save_reports_to_disk(project_reports: list[ProjectReport], user_report: UserReport):
    """
    Saves the project reports and user report to disk.

    Args:
        - project_reports: List of ProjectReport objects.
        - user_report: UserReport object.
    """

    dict_to_save = {
        "user_report": user_report.to_dict(),
        "project_reports": {pr.project_name: pr.to_dict() for pr in project_reports}
    }

    with open("artifact_miner_reports.json", "w") as f:
        import json
        json.dump(dict_to_save, f, indent=4, default=str)


def start_miner(zipped_file: str, email: Optional[str] = None) -> None:
    """
    This function defines the main application
    logic for the Artifact Miner. Currently,
    results are printed to the terminal

    Args:
        - zipped_file : The filepath to the zipped file.
        - email: Email associated with git account
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
            project_path=project.root_path,
            file_reports=file_reports,
            user_email=email
        )

        project_reports.append(pr)

    user_report = UserReport(project_reports)

    save_reports_to_disk(project_reports, user_report)

    print(user_report.to_user_readable_string())


if __name__ == '__main__':
    from classes.cli import ArtifactMiner
    ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference
