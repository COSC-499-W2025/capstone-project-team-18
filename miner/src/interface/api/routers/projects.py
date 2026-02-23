import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import SQLModel
from typing import Optional
from datetime import datetime

from src.interface.api.routers.util import get_session
from src.database.api.CRUD.projects import get_project_report_model_by_name
from src.services.mining_service import start_miner_service
from src.database.api.models import UserConfigModel as UserConfig

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

class UploadProjectResponse(SQLModel):
    message: str
    portfolio_name: str


@router.post("/upload", response_model=UploadProjectResponse)
def upload_project(
    file: UploadFile = File(...),
    email: Optional[str] = None,
    session=Depends(get_session)
):
    """Upload a zipped project file for analysis."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only .zip files are supported"
        )

    try:
        file_bytes = file.file.read()
        portfolio_name = os.path.splitext(file.filename)[0]

        user_config = UserConfig(
            consent=True,
            user_email=email,
        )

        start_miner_service(
            zipped_bytes=file_bytes,
            zipped_format=".zip",
            user_config=user_config
        )

        return UploadProjectResponse(
            message="Project uploaded and analyzed successfully",
            portfolio_name=portfolio_name
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process project: {str(e)}"
        )


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
