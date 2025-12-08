'''
This file contains all functions that will be called when we
want to access data from the database. In SQL, this would be
queries like SELECT, etc.
'''
from src.classes.statistic import StatisticIndex, Statistic, FileStatCollection, ProjectStatCollection, UserStatCollection, FileDomain, CodingLanguage, WeightedSkills
from src.classes.report import FileReport, ProjectReport, UserReport
from src.database.db import ProjectReportTable, UserReportTable, get_engine
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm import Session
from sqlalchemy import select

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _project_report_from_row(row: ProjectReportTable, engine) -> ProjectReport:
    """
    Build a ProjectReport directly from a ProjectReportTable row.

    This avoids assuming global uniqueness of project names by using
    the already-associated row to reconstruct the report.
    """
    statistics = StatisticIndex()

    for stat_template in ProjectStatCollection:
        column_name = stat_template.value.name.lower()

        if hasattr(row, column_name):
            value = getattr(row, column_name)
            if value is not None:

                # Rebuild non-JSON serializable enums
                if column_name == 'coding_language_ratio':
                    lang_ratios: dict[CodingLanguage, float] = {}
                    for key, val in value.items():
                        for lang in CodingLanguage:
                            if lang.value[0].lower() == str(key).lower():
                                lang_ratios[lang] = val
                                break
                    value = lang_ratios
                elif column_name == 'activity_type_contributions':
                    activity_contributions: dict[FileDomain, float] = {}
                    for key, val in value.items():
                        for domain in FileDomain:
                            if domain.value.lower() == str(key).lower():
                                activity_contributions[domain] = val
                                break
                    value = activity_contributions

                elif column_name == 'project_skills_demonstrated' or column_name == 'project_frameworks':
                    proj_skills: list[WeightedSkills] = []
                    for skill in value:
                        skill = WeightedSkills(
                            skill['skill_name'], skill['weight'])
                        proj_skills.append(skill)
                    value = proj_skills

                statistics.add(Statistic(stat_template.value, value))

    name = row.project_name or "Unknown Project"

    return ProjectReport(
        file_reports=get_file_reports(row, engine),
        project_name=name,
        statistics=statistics,
    )


def get_project_from_project_name(proj_name: str, engine=None) -> ProjectReport:
    '''
    Retrieves the row that corresponds to the given project name
    and converts it into a `ProjectReport` object.

    Args:
        proj_name (str): The name of the project report
        to retrieve (given by the user)

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
            return _project_report_from_row(result, engine)

        # Each project name should be unique, throw error if 0 rows or > 1 rows are returned
        except NoResultFound:
            logging.error(f'Error: No project found with name "{proj_name}"')
            raise
        except MultipleResultsFound:
            logging.error(
                f'Error: Multiple projects found with name "{proj_name}"')
            raise


def get_file_reports(report: ProjectReportTable, engine) -> list[FileReport]:
    '''
    Helper function for `get_project_from_project_name()`.
    For a given project report's ID in the database, get all of,
    the rows in `file_report`, convert them to `FileReport`
    objects, and return a list of the objects.
    - That is, for a project report that is stored in the database,
    get the file reports that were used to make the project report.
    '''
    with Session(engine) as session:
        file_report_rows = report.file_reports  # List[FileReportTable]

        if len(file_report_rows) == 0 or file_report_rows is None:
            raise ValueError(
                f'Error: No file report(s) found for project with id {id}')

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


def get_user_report(name: str, engine=None) -> UserReport:
    '''
    Retrieves the row that corresponds to the given user
    report's name and converts it into a `UserReport` object.

    Args:
        name (str): The name of the user report to retrieve (given by the user)

    Returns:
        UserReport
    '''

    # for testing purposes, we need to be able to pass the engine for
    # the temporary database to the function when we call it.
    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        try:
            # First, get the row that matches the given name
            result = session.execute(
                select(UserReportTable)
                .where(UserReportTable.title == name)
            ).scalars().one()  # UserReport object

            statistics = StatisticIndex()

            # Build the UserReport-level statistics
            for stat_template in UserStatCollection:
                column_name = stat_template.value.name.lower()

                # get stat if col exists and has value
                if hasattr(result, column_name):
                    value = getattr(result, column_name)
                    if value is not None:

                        if column_name == 'user_coding_language_ratio':
                            lang_ratios: dict[CodingLanguage, float] = {}
                            for key, val in value.items():
                                for lang in CodingLanguage:
                                    if lang.value[0].lower() == str(key).lower():
                                        lang_ratios[lang] = val
                                        break
                            value = lang_ratios

                        elif column_name == 'user_skills':
                            proj_skills: list[WeightedSkills] = []
                            for skill in value:
                                skill = WeightedSkills(
                                    skill['skill_name'], skill['weight'])
                                proj_skills.append(skill)
                            value = proj_skills

                        statistics.add(Statistic(stat_template.value, value))

            if result.title:
                name = result.title
            else:
                raise ValueError(
                    f"Error: Missing user report's name. Value stored in DB: {result.title}")

            # Build the list of ProjectReports that correspond the the UserReport
            project_reports = []

            # List[ProjectReportTable]
            project_report_rows = result.project_reports

            if len(project_report_rows) == 0 or project_report_rows is None:
                raise ValueError(
                    f'Error: No project report(s) found for user report with name {name}')

            for row in project_report_rows:
                # Build directly from associated rows to avoid global name collisions
                project_reports.append(_project_report_from_row(row, engine))

            # make the UserReport obj
            user_report = UserReport(
                project_reports=project_reports,
                report_name=name,
                statistics=statistics
            )

            return user_report

        # Each project name should be unique, throw error if 0 rows or > 1 rows are returned
        except NoResultFound:
            logging.error(f'Error: No user report found with name "{name}"')
            raise
        except MultipleResultsFound:
            logging.error(
                f'Error: Multiple user reports found with name "{name}"')
            raise
