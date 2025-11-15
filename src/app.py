"""
This file is the starting script for the application.
It provides logic for the CLI that the user will
interact with to begin the artifact miner.
- To start the CLI tool, run this file.
"""
from sqlalchemy.orm import Session

from utils.zipped_utils import unzip_file
from utils.project_discovery import discover_projects
from classes.analyzer import extract_file_reports
from classes.report import ProjectReport, UserReport
import tempfile
from database.db import get_engine
from database.utils.database_modify import create_row


def start_miner(zipped_file: str, email: str = None) -> None:
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

    file_report_rows = [] # will store FileReportTable objs
    engine = get_engine()
    with Session(engine) as session:

        # For each project, extract file reports and create ProjectReports
        project_reports = []  # Stores ProjectReport objs
        project_report_rows = []  # Stores ProjectReportTable objs

        for project in project_list:
            file_reports = extract_file_reports(project) # get the project's FileReports

            if file_reports is None:
                continue # skip if directory is empty

            # create the rows for the file reports
            for fr in file_reports:
                file_report = create_row(fr)
                file_report_rows.append(file_report)

            # make a ProjectReport with the FileReports
            project_report = ProjectReport(
                project_name=project.name,
                file_reports=file_reports,
                user_email=email
            )
            project_reports.append(project_report) # store ProjectReports for UserReport

            # create project_report row and configure FK relations
            project_row = create_row(report=project_report)
            project_row.file_reports.extend(file_report_rows)  # type: ignore
            project_report_rows.append(project_row)

        # make a UserReport with the ProjectReports
        user_report = UserReport(project_reports)

        # create a user_report row and configure FK relations
        user_row = create_row(report=user_report)
        user_row.project_reports.extend(project_report_rows)  # type: ignore

        # Insert all of the rows into the database
        session.add_all([user_row])  # type: ignore
        session.commit()

        print(user_report.to_user_readable_string())


if __name__ == '__main__':
    from classes.cli import ArtifactMiner
    ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference
