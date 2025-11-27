'''
This file contains all functions that will be called when we
want to access data from the database. In SQL, this would be
queries like SELECT, etc.
'''
from src.classes.statistic import StatisticIndex, Statistic, ProjectStatCollection, FileStatCollection, FileDomain, CodingLanguage
from src.classes.report import ProjectReport, FileReport, UserReport
from src.database.db import ProjectReportTable, UserReportTable, get_engine, __repr__
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm import Session
from sqlalchemy import select
from pprint import pprint


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_user_report_titles(engine=None) -> list[str]:
    """
    Return a list of all stored user report titles.
    """
    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        titles = session.execute(select(UserReportTable.title)).scalars().all()
        return [t for t in titles if t]


def get_user_report_by_zipped_filepath(zipped_filepath: str, engine=None) -> UserReport:
    """
    Retrieve a stored user report by its zipped filepath.
    """
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:
        try:
            result = session.execute(
                select(UserReportTable).where(UserReportTable.zipped_filepath == zipped_filepath)
            ).scalars().one()
        except NoResultFound:
            logging.error(
                f'Error: No user report found with zipped filepath "{zipped_filepath}"')
            raise
        except MultipleResultsFound:
            logging.error(
                f'Error: Multiple user reports found with zipped filepath "{zipped_filepath}"')
            raise

        project_reports = [
            _project_report_from_row(pr, engine) for pr in result.project_reports
        ]

        return UserReport(
            project_reports=project_reports,
            title=result.title or "",
            zipped_filepath=result.zipped_filepath or ""
        )


def user_report_title_exists(title: str, engine=None) -> bool:
    """
    Check if a user report with the provided title already exists.
    """
    return title in get_user_report_titles(engine)


def list_user_report_metadata(engine=None) -> list[dict[str, str]]:
    """
    Return a list of dictionaries describing saved user reports.
    Each entry contains at least a title and the associated zipped filepath.
    """
    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        reports = session.execute(select(UserReportTable)).scalars().all()
        metadata: list[dict[str, str]] = []
        for r in reports:
            metadata.append(
                {
                    "title": r.title or "",
                    "zipped_filepath": r.zipped_filepath or "",
                }
            )
        return metadata


def get_project_from_project_name(proj_name: str, engine=None) -> ProjectReport:
    '''
    Retrieves the row that corresponds to the given project name
    and converts it into a `ProjectReport` object.

    Args:
        proj_name (str): The name of the project (given by the user)

    Returns:
        ProjectReport
    '''

    # for testing purposes, we need to be able to pass the engine for
    # the temporary database to the function when we call it.
    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        try:
            result = session.execute(
                select(ProjectReportTable)
                .where(ProjectReportTable.project_name == proj_name)
            ).scalars().one()  # ProjectReportTable object

            statistics = StatisticIndex()

            for stat_template in ProjectStatCollection:
                column_name = stat_template.value.name.lower()

                # get stat if col exists and has value
                if hasattr(result, column_name):
                    value = getattr(result, column_name)
                    if value is not None:
                        statistics.add(Statistic(stat_template.value, value))

            if result.project_name:
                name = result.project_name
            else:
                name = "Unknown Project"

            # make the ProjectReport obj
            project_report = ProjectReport(
                file_reports=get_file_reports(result.id, engine),
                project_name=name,
                statistics=statistics,
            )

            return project_report

        # Each project name should be unique, throw error if 0 rows or > 1 rows are returned
        except NoResultFound:
            logging.error(f'Error: No project found with name "{proj_name}"')
            raise
        except MultipleResultsFound:
            logging.error(
                f'Error: Multiple projects found with name "{proj_name}"')
            raise


def get_file_reports(id: int, engine) -> list[FileReport]:
    '''
    Helper function for `get_project_from_project_name()`.
    For a given project report's ID in the database, get all of,
    the rows in `file_report`, convert them to `FileReport`
    objects, and return a list of the objects.
    - That is, for a project report that is stored in the database,
    get the file reports that were used to make the project report.
    '''
    with Session(engine) as session:
        project = session.get(ProjectReportTable, id)

        if project is None:
            logging.error(f'Error: No project with id {id}')
            raise ValueError()

        file_report_rows = project.file_reports  # List[FileReportTable]

        if len(file_report_rows) == 0 or file_report_rows is None:
            logging.error(
                f'Error: No file report(s) found for project with id {id}')
            raise ValueError()

        file_reports = []
        for row in file_report_rows:
            statistics = StatisticIndex()

            # get stats
            for stat_template in FileStatCollection:
                column_name = stat_template.value.name.lower()

                # get stat if col exists and has value
                if hasattr(row, column_name):
                    value = getattr(row, column_name)
                    try:
                        if value is not None:
                            # Some stats store non-primitive data types, but the db stores them
                            # as primitives, so we need to convert them back.
                            if column_name == "type_of_file":
                                value = FileDomain(value)
                            if column_name == "coding_language":
                                # CodingLanguage stores tuples: e.g., ("Python", [".py", ...])
                                # Find the enum member with matching value
                                for lang in CodingLanguage:
                                    if lang.value[0] == value[0]:  # type: ignore
                                        value = lang
                                        break
                            statistics.add(
                                Statistic(stat_template.value, value))
                    except Exception as e:
                        raise ValueError(
                            f"Error: {e} when getting value in file_report for column {column_name}")

            file_report = FileReport(statistics, row.filepath)
            file_reports.append(file_report)
        return file_reports


def _project_report_from_row(row: ProjectReportTable, engine) -> ProjectReport:
    """
    Build a ProjectReport from an existing ProjectReportTable row.
    """
    statistics = StatisticIndex()

    for stat_template in ProjectStatCollection:
        column_name = stat_template.value.name.lower()

        if hasattr(row, column_name):
            value = getattr(row, column_name)
            if value is not None:
                statistics.add(Statistic(stat_template.value, value))

    name = row.project_name or "Unknown Project"

    project_report = ProjectReport(
        file_reports=get_file_reports(row.id, engine),
        project_name=name,
        statistics=statistics,
    )
    return project_report


def get_user_report_by_title(title: str, engine=None) -> UserReport:
    """
    Retrieve a stored user report and rebuild the object by its unique title.
    """
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:
        try:
            result = session.execute(
                select(UserReportTable).where(UserReportTable.title == title)
            ).scalars().one()
        except NoResultFound:
            logging.error(f'Error: No user report found with title "{title}"')
            raise
        except MultipleResultsFound:
            logging.error(
                f'Error: Multiple user reports found with title "{title}"')
            raise

        project_reports = [
            _project_report_from_row(pr, engine) for pr in result.project_reports
        ]

        return UserReport(
            project_reports=project_reports,
            title=result.title or "",
            zipped_filepath=result.zipped_filepath or ""
        )
