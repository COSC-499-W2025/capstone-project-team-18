"""
This file is the starting script for the application.
It provides logic for the CLI that the user will
interact with to begin the artifact miner.
- To start the CLI tool, run this file.
"""
from typing import Optional, Callable
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from src.utils.zipped_utils import unzip_file
from src.utils.project_discovery.project_discovery import discover_projects
from src.utils.print_resume_and_portfolio import resume_CLI_stringify, portfolio_CLI_stringify

from src.classes.analyzer import extract_file_reports
from src.classes.report import ProjectReport, UserReport
from src.classes.resume.render import ResumeLatexRenderer

from src.database.db import get_engine, Base
from src.database.utils.database_modify import create_row


def start_miner(
    zipped_file: str,
    email: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None
) -> None:
    """
    This function defines the main application
    logic for the Artifact Miner. Currently,
    results are printed to the terminal

    Args:
        - zipped_file : The filepath to the zipped file.
        - email: Email associated with git account
    """

    # Import inside function to avoid circular import
    from src.classes.cli import UserPreferences

    # Load preferences to get language filter
    prefs = UserPreferences()
    language_filter = prefs.get("languages_to_include", [])

    # =================== Unzip Stage ===================

    # Unzip the zipped file into temporary directory
    unzipped_dir = tempfile.mkdtemp(prefix="artifact_miner_")
    unzip_file(zipped_file, unzipped_dir)

    # =================== Discovery stage ===================

    project_list = discover_projects(unzipped_dir)

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

            if file_reports is None:
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

        # Update at END of all project analysis
        if progress_callback:
            progress_callback("analysis", total_projects, total_projects, "")

        # =================== Saving stage ===================
        if progress_callback:
            progress_callback("saving", 1, 1, "")

        # make a UserReport with the ProjectReports
        dir_name = Path(zipped_file).stem  # name of zipped dir
        user_report = UserReport(project_reports, dir_name)
        # create a user_report row and configure FK relations
        user_row = create_row(report=user_report)
        user_row.project_reports.extend(project_report_rows)  # type: ignore

        # Insert all of the rows into the database (INSIDE the session block)
        session.add_all([user_row])  # type: ignore
        session.commit()

        # =================== Analysis Complete ===================
        if progress_callback:
            progress_callback("complete", 1, 1, "")

    print("-------- Analysis Reports --------\n")
    resume = user_report.generate_resume(email)

    # Download latex resume to file system
    latex_str = resume.export(ResumeLatexRenderer())

    with open("resume.tex", "w", encoding="utf-8") as f:
        f.write(latex_str)

    # Print the resume items
    resume_CLI_stringify(resume)

    # Print the portfolio item
    portfolio_CLI_stringify(user_report)


if __name__ == '__main__':
    from src.classes.cli import ArtifactMiner

    try:
        ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference

    except KeyboardInterrupt:
        print("Exiting the program...")
