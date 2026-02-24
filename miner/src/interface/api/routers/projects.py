from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel
from typing import Optional, List
from datetime import datetime

from src.interface.api.routers.util import get_session
from src.database.api.CRUD.projects import (
    get_project_report_model_by_name,
    get_project_report_by_name,
)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


class ProjectReportResponse(SQLModel):
    project_name: str
    user_config_used: Optional[int]
    image_data: Optional[bytes]
    created_at: datetime
    last_updated: datetime

class ProjectShowcaseResponse(SQLModel):
    project_name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frameworks: List[str] = []
    bullet_points: List[str] = []


@router.post("/upload")
def upload_project():
    return {"message": "Project uploaded"}


@router.get("")
def list_projects():
    return {"projects": []}


@router.get("/{project_name}", response_model=ProjectReportResponse)
def get_project(project_name: str, session=Depends(get_session)):

    result = None

    try:
        result = get_project_report_model_by_name(session, project_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve project report {e}"
        )

    if not result:
        raise HTTPException(
            status_code=404, detail=f"No project report named {project_name}"
        )

    return result

@router.get("/{project_name}/showcase", response_model=ProjectShowcaseResponse)
def get_project_showcase(project_name: str, session=Depends(get_session)):

    try:
        report = get_project_report_by_name(session, project_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve project report {e}"
        )

    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No project report named {project_name}"
        )

    resume_item = report.generate_resume_item()

    # Helper to normalize date → datetime
    def _to_datetime(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.combine(value, datetime.min.time())
        except Exception:
            return None

    return ProjectShowcaseResponse(
        project_name=report.project_name,
        start_date=_to_datetime(resume_item.start_date),
        end_date=_to_datetime(resume_item.end_date),
        frameworks=list(resume_item.frameworks or []),
        bullet_points=list(resume_item.bullet_points or []),
    )