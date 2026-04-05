import base64
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import field_serializer
from sqlmodel import Field, SQLModel
from src.database.api.CRUD.projects import (get_all_project_report_models,
                                            get_project_report_model_by_name)
from src.database.api.CRUD.user_config import get_most_recent_user_config
from src.database.api.models import ProjectReportModel
from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.services.mining_service import start_miner_service
from src.utils.errors import DatabaseOperationError, ProjectNotFoundError

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

    @field_serializer("image_data")
    def encode_image_data(self, value: Optional[bytes]) -> Optional[str]:
        if value is None:
            return None
        return base64.b64encode(value).decode("utf-8")


class UploadProjectResponse(SQLModel):
    message: str


class ProjectListResponse(SQLModel):
    projects: List[ProjectReportResponse]
    count: int


@router.post("/upload", response_model=UploadProjectResponse)
def upload_project(
    file: UploadFile = File(...),
    session=Depends(get_session)
):
    """
    Ingest a compressed project archive, analyze its contents, and persist the results.

    Supported archive formats: `.tar.gz`, `.gz`, `.7z`, `.zip`.

    The most recent UserConfig (email, GitHub username, consent) is loaded from the
    database and passed to the miner so all persisted settings are applied during mining.

    Form parameters:
    - `file`: The compressed project archive to analyze.

    Returns:
    - 200: An `UploadProjectResponse` with a confirmation message.

    Raises:
    - 400: The file extension is not a supported archive format.
    - 422: The archive content is malformed or otherwise invalid.
    - 500 `DATABASE_OPERATION_FAILED`: An unexpected error occurred during processing.
    """
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

        user_config = get_most_recent_user_config(session)

        start_miner_service(
            zipped_bytes=file_bytes,
            zipped_format=matched_format,
            user_config=user_config
        )

        return UploadProjectResponse(
            message="Project uploaded and analyzed successfully"
        )

    except ValueError as e:
        logger.warning("Invalid input during project upload: %s", str(e))
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error during project upload: %s", str(e))
        raise DatabaseOperationError(
            f"Failed to process project: {str(e)}") from e


@router.get(
    "/",
    response_model=ProjectListResponse,
)
def list_projects(session=Depends(get_session)):
    """
    List all project reports ordered by representation_rank, then creation date.

    Returns:
    - 200: A `ProjectListResponse` with an ordered list of all project reports and a count.

    Raises:
    - 500 `DATABASE_OPERATION_FAILED`: An unexpected error occurred while fetching the project list.
    """
    try:

        all_projects = get_all_project_report_models(session)

        # rank first (None ranks go after)
        all_projects.sort(
            key=lambda p: (
                p.representation_rank is None,
                p.representation_rank if p.representation_rank is not None else 10**9,
                p.created_at,
            )
        )

        return ProjectListResponse(
            projects=all_projects,
            count=len(all_projects)
        )

    except Exception as e:
        logger.error(f"Error fetching project list: {str(e)}")
        raise DatabaseOperationError(
            f"Failed to retrieve the list of projects from the database: {type(e).__name__}: {str(e)}"
        ) from e


@router.get("/{project_name}", response_model=ProjectReportResponse)
def get_project(project_name: str, session=Depends(get_session)):
    """
    Retrieve a single project report record by project name.

    Path parameters:
    - `project_name`: The unique name of the project.

    Returns:
    - 200: A `ProjectReportResponse` for the matched project.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: An unexpected error occurred while fetching the report.
    """
    result = None

    try:
        result = get_project_report_model_by_name(session, project_name)
    except Exception as e:
        raise DatabaseOperationError(
            f"Failed to retrieve project report: {e}") from e

    if not result:
        raise ProjectNotFoundError(f"No project report named {project_name}")

    return result


@router.post("/{project_name}/image")
def upload_project_image(
    project_name: str,
    file: UploadFile = File(...),
    session=Depends(get_session)
):
    """
    Attach an image file to the specified project.

    The file must be a valid image (content-type must start with `image/`).

    Path parameters:
    - `project_name`: The unique name of the project.

    Form parameters:
    - `file`: The image file to upload.

    Returns:
    - 200: `{"message": "Image successfully assigned to project '{project_name}'."}` on success.

    Raises:
    - 400: The uploaded file is not an image.
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: The image could not be saved; changes were rolled back.
    """

    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise ProjectNotFoundError(f"No project report named {project_name}")

    # Validate that the uploaded file is actually an image
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image."
        )

    try:
        # Read file bytes and update the model
        image_bytes = file.file.read()

        project_model.image_data = image_bytes
        project_model.last_updated = datetime.now(timezone.utc)

        session.add(project_model)
        session.commit()

        return {"message": f"Image successfully assigned to project '{project_name}'."}

    except Exception as e:
        session.rollback()
        logger.error("Error uploading image for project %s: %s",
                     project_name, str(e))
        raise DatabaseOperationError(
            f"Failed to upload image: {str(e)}") from e


@router.delete("/{project_name}/image")
def delete_project_image(
    project_name: str,
    session=Depends(get_session),
):
    """
    Remove the thumbnail image from the specified project.

    Path parameters:
    - `project_name`: The name of the project to remove the image from.

    Returns:
    - 200: `{"message": "..."}` on success.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: The image could not be removed; changes were rolled back.
    """
    project_model = session.query(ProjectReportModel).filter_by(project_name=project_name).first()
    if not project_model:
        raise ProjectNotFoundError(f"No project report named {project_name}")

    try:
        project_model.image_data = None
        project_model.last_updated = datetime.now(timezone.utc)

        session.add(project_model)
        session.commit()

        return {"message": f"Image successfully removed from project '{project_name}'."}

    except Exception as e:
        session.rollback()
        logger.error("Error removing image for project %s: %s",
                     project_name, str(e))
        raise DatabaseOperationError(
            f"Failed to remove image: {str(e)}") from e
