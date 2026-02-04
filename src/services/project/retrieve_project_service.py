"""
Retrieval Services for a Project
"""

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from src.database.base import get_engine
from src.database.models.project_report_table import ProjectReportTable
from src.core.statistic import ProjectStatCollection


class ProjectResponse(BaseModel):
    """Response model for a single project"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_name: str
    project_path: str
    date_created: Optional[datetime] = None
    date_updated: Optional[datetime] = None
    statistics: Dict[str, Any]


class AllProjectsResponse(BaseModel):
    """Response model for all projects"""
    projects: list[ProjectResponse]


def retrieve_project_by_id(project_id: int) -> Optional[ProjectResponse]:
    """
    Retrieve a single project by ID

    :param project_id: The id of the project to retrieve
    :return: ProjectResponse or None if not found
    """
    engine = get_engine()

    with Session(engine) as session:
        project = session.query(ProjectReportTable).filter(
            ProjectReportTable.id == project_id
        ).first()

        if not project:
            return None

        # Build statistics dict from all project stat columns
        # ColumnStatisticSerializer automatically deserializes these values
        statistics = {}
        for stat_enum in ProjectStatCollection:
            stat_name = stat_enum.value.name
            column_name = stat_name.lower()
            value = getattr(project, column_name, None)
            if value is not None:
                statistics[stat_name] = value

        return ProjectResponse(
            id=project.id,
            project_name=project.project_name or "Unknown Project",
            project_path=project.project_path or "Unknown Path",
            date_created=project.project_start_date,
            date_updated=project.project_end_date,
            statistics=statistics
        )


def retrieve_projects() -> AllProjectsResponse:
    """
    Retrieve all available projects in the database

    :return: AllProjectsResponse containing all projects
    """
    engine = get_engine()

    with Session(engine) as session:
        project_rows = session.query(ProjectReportTable).all()

        projects = []
        for project in project_rows:
            # Build statistics dict from all project stat columns
            statistics = {}
            for stat_enum in ProjectStatCollection:
                stat_name = stat_enum.value.name
                column_name = stat_name.lower()
                value = getattr(project, column_name, None)
                if value is not None:
                    statistics[stat_name] = value

            projects.append(ProjectResponse(
                id=project.id,
                project_name=project.project_name or "Unknown Project",
                project_path=project.project_path or "Unknown Path",
                date_created=project.project_start_date,
                date_updated=project.project_end_date,
                statistics=statistics
            ))

        return AllProjectsResponse(projects=projects)