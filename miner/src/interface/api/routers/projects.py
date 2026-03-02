
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import SQLModel
from typing import Optional, List
from datetime import datetime

from src.interface.api.routers.util import get_session
from src.database.api.CRUD.projects import (
    get_project_report_model_by_name,
    get_project_report_by_name,
    get_all_project_report_models
)
from src.services.mining_service import start_miner_service
from src.database.api.models import UserConfigModel as UserConfig
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)

SUPPORTED_FORMATS = [".tar.gz", ".gz", ".7z", ".zip"]


class ProjectReportResponse(SQLModel):
    project_name: str
    user_config_used: Optional[int]
    image_data: Optional[bytes]
    created_at: datetime
    statistic: dict
    last_updated: datetime


class UploadProjectResponse(SQLModel):
    message: str
    portfolio_name: str


class ProjectListResponse(SQLModel):
    projects: List[ProjectReportResponse]
    count: int


class ProjectShowcaseResponse(SQLModel):
    project_name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frameworks: List[str] = []
    bullet_points: List[str] = []


@router.post("/upload", response_model=UploadProjectResponse)
def upload_project(
    file: UploadFile = File(...),
    email: Optional[str] = None,
    portfolio_name: Optional[str] = None,
    session=Depends(get_session)
):
    """Upload a zipped project file for analysis."""
    filename = file.filename or ""
    matched_format = next(
        (fmt for fmt in SUPPORTED_FORMATS if filename.endswith(fmt)), None
    )

    if not matched_format:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    try:
        file_bytes = file.file.read()

        # Use provided portfolio_name, otherwise derive from filename
        if not portfolio_name:
            portfolio_name = filename
            for fmt in SUPPORTED_FORMATS:
                if portfolio_name.endswith(fmt):
                    portfolio_name = portfolio_name[: -len(fmt)]
                    break

        user_config = UserConfig(
            consent=True,
            user_email=email,
        )

        start_miner_service(
            zipped_bytes=file_bytes,
            zipped_format=matched_format,
            user_config=user_config
        )

        return UploadProjectResponse(
            message="Project uploaded and analyzed successfully",
            portfolio_name=portfolio_name
        )

    except ValueError as e:
        logger.warning("Invalid input during project upload: %s", str(e))
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error during project upload: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process project: {str(e)}"
        )


@router.get(
    "/",
    response_model=ProjectListResponse,
)
def list_projects(session=Depends(get_session)):
    """
    Get all project reports without pagination.
    """
    try:

        all_projects = get_all_project_report_models(session)

        return ProjectListResponse(
            projects=all_projects,
            count=len(all_projects)
        )

    except Exception as e:
        logger.error(f"Error fetching project list: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve the list of projects from the database."
        )


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
    """
    GET /{project_name}/showcase

    This endpoint will retieve a passed in project_name and format it
    for a showcase. The idea is that user can select which project they
    would like to showcase through the UI, and the portfolio will call
    this endpoint to format that project for a showcase.

    Returns the project_name fromatted for project showcase.
    """
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
