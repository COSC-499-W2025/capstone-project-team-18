"""
This file is the starting script for the application.
It provides logic for the CLI that the user will
interact with to begin the artifact miner.
- To start the CLI tool, run this file.
"""
from sqlalchemy.orm import Session

from typing import Optional


from datetime import datetime
from pathlib import Path
from src.utils.zipped_utils import unzip_file
from src.utils.project_discovery import discover_projects
from src.classes.analyzer import extract_file_reports
from src.classes.report import ProjectReport, UserReport
import tempfile
from src.database.db import get_engine, Base
from src.database.utils.database_modify import create_row
from src.database.utils.database_access import get_user_report_titles


def _default_report_title(zipped_file: str) -> str:
    """Generate a timestamped default title based on the zipped file name."""
    base = Path(zipped_file).stem or "user-report"
    return f"{base}-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _ensure_unique_title(title: str, existing_titles: list[str]) -> str:
    """Append numeric suffixes until the title is unique."""
    candidate = title
    counter = 1
    while candidate in existing_titles:
        candidate = f"{title}-{counter}"
        counter += 1
    return candidate


def _prompt_for_title(existing_titles: list[str], zipped_file: str) -> str:
    """
    Prompt the user for a custom title and enforce uniqueness.
    Falls back to a generated default if left empty or cancelled.
    """
    prompt = (
        "\nEnter a title for this report (leave blank for a suggested default, "
        "or type 'back'/'cancel' to use the default): "
    )
    while True:
        answer = input(prompt).strip()

        if answer.lower() in ("exit", "quit"):
            raise SystemExit(0)

        if answer.lower() in ("back", "cancel"):
            default_title = _ensure_unique_title(
                _default_report_title(zipped_file), existing_titles)
            print(f"Using default title: {default_title}")
            return default_title

        if not answer:
            default_title = _ensure_unique_title(
                _default_report_title(zipped_file), existing_titles)
            print(f"Using default title: {default_title}")
            return default_title

        if answer in existing_titles:
            print("A report with that title already exists. Please try a different name.")
            continue

        return answer


def start_miner(zipped_file: str, email: Optional[str] = None, prompt_for_title: bool = False, report_title: Optional[str] = None) -> None:
    """
    This function defines the main application
    logic for the Artifact Miner. Currently,
    results are printed to the terminal

    Args:
        - zipped_file : The filepath to the zipped file.
        - email: Email associated with git account
        - prompt_for_title: If True, interactively ask the user to name the report
        - report_title: Optional pre-selected title to use when saving the report
    """

    # Unzip the zipped file into temporary directory
    unzipped_dir = tempfile.mkdtemp(prefix="artifact_miner_")
    unzip_file(zipped_file, unzipped_dir)

    project_list = discover_projects(unzipped_dir)

    engine = get_engine()

    # Create tables if they do not exist
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # For each project, extract file reports and create ProjectReports
        project_reports = []  # Stores ProjectReport objs
        project_report_rows = []  # Stores ProjectReportTable objs

        for project in project_list:
            file_reports = extract_file_reports(
                project, email)  # get the project's FileReports

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

        # make a UserReport with the ProjectReports
        user_report = UserReport(
            project_reports,
            title="",
            zipped_filepath=zipped_file
        )

        existing_titles = get_user_report_titles(engine)
        if prompt_for_title:
            final_title = _prompt_for_title(
                existing_titles, zipped_file) if report_title is None else report_title
            if final_title in existing_titles:
                print(
                    "A report with that title already exists. Please try a different name.")
                return
        else:
            chosen_title = report_title or _default_report_title(zipped_file)
            final_title = _ensure_unique_title(chosen_title, existing_titles)

        user_report.title = final_title
        # create a user_report row and configure FK relations
        user_row = create_row(report=user_report)
        user_row.project_reports.extend(project_report_rows)  # type: ignore

        # Insert all of the rows into the database (INSIDE the session block)
        session.add_all([user_row])  # type: ignore
        session.commit()

    print("-------- Analysis Reports --------\n")

    print("-------- Resume --------\n")
    print(user_report.generate_resume())
    print("------------------------\n")

    print("-------- Portfolio --------\n")
    print(user_report.to_user_readable_string())
    print("\n-------------------------\n")


if __name__ == '__main__':
    from src.classes.cli import ArtifactMiner
    ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference
