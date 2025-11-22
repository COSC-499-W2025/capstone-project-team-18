'''
This file contains all functions that will be called when we
want to access data from the database. In SQL, this would be
queries like SELECT, etc.
'''
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, MultipleResultsFound


from src.database.db import ProjectReportTable, get_engine, __repr__
from src.classes.report import ProjectReport, FileReport
from src.classes.statistic import StatisticIndex, Statistic, ProjectStatCollection, FileStatCollection, FileDomain, CodingLanguage

engine = get_engine()


def get_project_from_project_name(proj_name: str) -> ProjectReport:
    '''
    Retrieves the row that corresponds to the given project name
    and converts it into a `ProjectReport object.

    Args:
        proj_name (str): The name of the project (given by the user)

    Returns:
        ProjectReport

    '''
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
                file_reports=get_file_reports(result.id),
                project_name=name,
                statistics=statistics,
            )

            return project_report

        # Each project name should be unique, throw error if 0 rows or > 1 rows are returned
        except NoResultFound:
            # TODO replace w/ logger
            print(f'Error: No project found with name "{proj_name}"')
            raise
        except MultipleResultsFound:
            # TODO replace w/ logger
            print(f'Error: Multiple projects found with name "{proj_name}"')
            raise


def get_file_reports(id: int) -> list[FileReport]:
    '''
    For a given project report's ID in the database, get all of,
    the rows in `file_report`, convert them to `FileReport`
    objects, and return a list of the objects.
    - That is, for a project report that is stored in the database,
    get the file reports that were used to make the project report.
    '''
    with Session(engine) as session:
        project = session.get(ProjectReportTable, id)

        if project is None:
            raise ValueError(f'Error: No project with id {id}')

        file_report_rows = project.file_reports  # List[FileReportTable]

        if file_report_rows is None:
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
                        statistics.add(Statistic(stat_template.value, value))

            file_report = FileReport(statistics, row.filepath)
            file_reports.append(file_report)
        return file_reports
