'''
This file contains all functions that will be called when we
want to modify or add data to the database. In SQL, this
would be queries like INSERT, UPDATE, etc.
'''

from src.core.report import FileReport, ProjectReport, UserReport
from src.infrastructure.database.db import FileReportTable, ProjectReportTable, UserReportTable

from sqlalchemy.orm import Session
from sqlalchemy import select
from src.infrastructure.database.db import get_engine


def create_row(report: FileReport | ProjectReport | UserReport):
    '''
    Returns a new row for a given type of report object.
    - Equivalent to an SQL `INSERT` statement.

    Example: a new row for the `file_report`
    table (i.e., a new `FileReportTable` object) is
    returned) if a `FileReport` object is passed in.
    '''
    if isinstance(report, FileReport):
        row = FileReportTable()
        row.filepath = report.filepath
    elif isinstance(report, ProjectReport):
        row = ProjectReportTable()
        if report.project_name:
            row.project_name = report.project_name
        if report.project_path:
            row.project_path = report.project_path

    elif isinstance(report, UserReport):
        row = UserReportTable()
        if report.report_name:
            row.title = report.report_name
    else:
        raise ValueError(f"Unknown report type: {type(report)}")

    # We iterate through all the statistics in the report and set
    # the corresponding column in the row to the statistic's value.
    # Serialization is done with .types.py SerializableJSON type.
    for stat in report.statistics:
        col_name = stat.get_template().name.lower()
        value = stat.value

        if hasattr(row, col_name):
            setattr(row, col_name, value)

    return row


def delete_user_report_and_related_data(report_id=None, title=None, zipped_filepath=None, engine=None):
    """
    Delete a user report and all related project and file reports by id, title, or zipped_filepath.
    Args:
        report_id (int): ID of the user report to delete.
        title (str): Title of the user report to delete.
        zipped_filepath (str): Filepath to the zipped file to delete.
    """
    if engine is None:
        engine = get_engine()

    try:
        with Session(engine) as session:
            query = session.query(UserReportTable)
            user_report = None
            if report_id is not None:
                user_report = session.get(UserReportTable, report_id)
            elif title is not None:
                user_report = query.filter_by(title=title).first()
            elif zipped_filepath is not None:
                user_report = query.filter_by(
                    zipped_filepath=zipped_filepath).first()
            else:
                raise ValueError(
                    "Must provide report_id, title, or zipped_filepath")

            if not user_report:
                raise ValueError("User report not found")

            # Find and delete project reports only associated with this user report
            for project_report in list(user_report.project_reports):
                if len(project_report.user_reports) == 1:
                    session.delete(project_report)
            user_report.project_reports.clear()
            session.flush()
            session.delete(user_report)
            session.commit()
            return True
    except ValueError:
        # Let ValueError propagate for test and caller handling
        raise
    except Exception as e:
        print(f"Error deleting user report and related data: {e}")
        return False


def rename_user_report(current_title: str, new_title: str, engine=None) -> tuple[bool, str]:
    """
    Rename a user report if the new title is unique.
    If multiple rows share the current title, the most recently created
    (highest id) row is renamed to avoid collisions.

    Args:
        current_title (str): Existing title to update.
        new_title (str): Desired unique title.
        engine: Optional SQLAlchemy engine (used in tests).

    Returns:
        tuple[bool, str]: Success flag and status message.
    """
    if engine is None:
        engine = get_engine()

    if not new_title:
        return False, "New title cannot be empty"

    if new_title == current_title:
        return True, f"Keeping existing title '{current_title}'"

    with Session(engine) as session:
        current = session.execute(
            select(UserReportTable)
            .where(UserReportTable.title == current_title)
            .order_by(UserReportTable.id.desc())
        ).scalars().first()

        if current is None:
            return False, f"Portfolio '{current_title}' not found"

        conflict = session.execute(
            select(UserReportTable).where(UserReportTable.title == new_title)
        ).scalar_one_or_none()

        if conflict is not None:
            return False, f"Portfolio title '{new_title}' already exists"

        current.title = new_title
        session.commit()
        return True, f"Portfolio renamed to '{new_title}'"
