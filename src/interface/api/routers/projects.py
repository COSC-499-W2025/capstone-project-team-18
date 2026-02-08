from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel
from typing import Optional
from datetime import datetime

from src.interface.api.routers.util import get_session
from src.database.api.CRUD.projects import get_project_report_model_by_name

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
