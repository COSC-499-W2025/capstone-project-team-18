from fastapi import APIRouter,  Depends, HTTPException
from sqlmodel import SQLModel
from typing import List, Optional
import datetime

from src.interface.api.routers.util import get_session
from src.interface.api.routers.user_config import get_user_config_safe
from src.database import (
    get_project_report_by_name
)
from src.database.api.CRUD.resume import save_resume, load_resume, get_resume_model_by_id
from src.core.report.user.user_report import UserReport
from src.utils.errors import ResumeNotFoundError, ProjectNotFoundError, DatabaseOperationError
from datetime import date

router = APIRouter(
    prefix="/resume",
    tags=["resume"],
)

# ---------- Request/Response Models ----------
class GenerateResumeRequest(SQLModel):
    """Request model for generating a resume"""
    project_names: List[str]
    user_config_id: Optional[int] = None


class EditResumeMetadataRequest(SQLModel):
    """Request model for editing a resume"""
    email: Optional[str] = None
    github_username: Optional[str] = None


class EditBulletPointRequest(SQLModel):
    resume_id: int
    item_index: int
    new_content: str

    # Are we adding a new bullet?
    append: bool

    # If not appending, need what index we are overwritting
    bullet_point_index: Optional[int]


class EditResumeItemMetadataRequest(SQLModel):
    resume_id: int
    item_index: int

    start_date: datetime.date
    end_date: datetime.date
    title: str


class ResumeItemResponse(SQLModel):
    """Response model for a resume item"""
    id: Optional[int] = None
    resume_id: Optional[int] = None
    project_name: Optional[str] = None
    title: str
    frameworks: List[str]
    bullet_points: List[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ResumeResponse(SQLModel):
    """Response model for a resume with items"""
    id: Optional[int] = None
    email: Optional[str] = None
    github: Optional[str] = None
    skills: List[str]
    education: List[str] = []
    awards: List[str] = []
    items: List[ResumeItemResponse] = []
    created_at: Optional[datetime.datetime]
    last_updated: Optional[datetime.datetime]


# ---------- Resume API Endpoints ----------
@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, session=Depends(get_session)):
    """
    Retrieve a saved resume by its database ID.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Returns:
    - 200: A `ResumeResponse` with metadata and all resume items.

    Raises:
    - 404 `RESUME_NOT_FOUND`: No resume exists with the given ID.
    """

    result = get_resume_model_by_id(session, resume_id)

    if not result:
        raise ResumeNotFoundError(f"No resume found with id {resume_id}")

    return result


@router.post("/generate", response_model=ResumeResponse)
def generate_resume(request: GenerateResumeRequest, session=Depends(get_session)):
    """
    Generate a new resume from one or more project reports.

    Education and awards are sourced from the user's ResumeConfigModel when a
    user_config_id is provided.

    Body parameters:
    - `project_names`: Non-empty list of project names to include in the resume.
    - `user_config_id`: Optional ID of the UserConfig record to pull education and
      awards from.

    Returns:
    - 200: A `ResumeResponse` for the newly created resume.

    Raises:
    - 400: project_names is empty.
    - 404 `PROJECT_NOT_FOUND`: A named project does not exist in the database.
    - 404 `USER_CONFIG_NOT_FOUND`: The specified user_config_id does not exist.
    - 500 `DATABASE_OPERATION_FAILED`: Resume generation or persistence failed;
      changes were rolled back.
    """

    if not request.project_names:
        raise HTTPException(
            status_code=400, detail="At least one project name is required")

    # Get user config
    user_config = get_user_config_safe(session, request.user_config_id)

    # Get projects as domain objects
    project_reports = []
    for project_name in request.project_names:
        project = get_project_report_by_name(session, project_name)
        if not project:
            raise ProjectNotFoundError(f"No project found with name '{project_name}'")
        project_reports.append(project)

    try:
        # Generate resume
        user_report = UserReport(
            project_reports=project_reports, report_name="Generated Resume")

        # Extract email and github from user config
        user_email = user_config.user_email if user_config else None
        user_github = user_config.github if user_config else None

        # Extract education/awards from ResumeConfigModel
        user_education = []
        user_awards = []
        if user_config and user_config.resume_config:
            user_education = user_config.resume_config.education or []
            user_awards = user_config.resume_config.awards or []

        # Generate resume with email, github, education and awards
        resume_domain = user_report.generate_resume(
            user_email,
            user_github,
            education=user_education,
            awards=user_awards

        )

        # Save using serialize_resume
        resume_model = save_resume(session, resume_domain)
        session.commit()

        return resume_model

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(f"Failed to generate resume: {str(e)}") from e


@router.post("/{resume_id}/edit/metadata", response_model=ResumeResponse)
def edit_resume_metadata(
    resume_id: int,
    request: EditResumeMetadataRequest,
    session=Depends(get_session)
):
    """
    Update the top-level metadata fields (email, github) of an existing resume.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Body parameters:
    - `email`: Optional new email address.
    - `github_username`: Optional new GitHub username.

    Returns:
    - 200: The updated `ResumeResponse`.

    Raises:
    - 404 `RESUME_NOT_FOUND`: No resume exists with the given ID.
    - 500 `DATABASE_OPERATION_FAILED`: The edit failed; changes were rolled back.
    """

    # Load as domain object
    resume_domain = load_resume(session, resume_id)

    if not resume_domain:
        raise ResumeNotFoundError(f"No resume found with id {resume_id}")

    try:
        # Update fields
        if request.email is not None:
            resume_domain.email = request.email

        if request.github_username is not None:
            resume_domain.github = request.github_username

        # Save updated (uses serialize_resume)
        updated_model = save_resume(session, resume_domain)
        updated_model.id = resume_id

        session.commit()

        return updated_model

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(f"Failed to edit resume: {str(e)}") from e


@router.post("/{resume_id}/edit/bullet_point", response_model=ResumeResponse)
def edit_resume_item_bullet_point(
    resume_id: int,
    request: EditBulletPointRequest,
    session=Depends(get_session)
):
    """
    Edit or append a bullet point in a specific resume item.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Body parameters:
    - `item_index`: Zero-based index of the resume item to edit.
    - `new_content`: Replacement or appended bullet point text.
    - `append`: If true, appends `new_content` as a new bullet; otherwise overwrites
      at `bullet_point_index`.
    - `bullet_point_index`: Required when `append` is false; zero-based index of the
      bullet to overwrite.

    Returns:
    - 200: The updated `ResumeResponse`.

    Raises:
    - 400: item_index is out of bounds.
    - 400: bullet_point_index is not provided when append is false, or is out of bounds.
    - 404 `RESUME_NOT_FOUND`: No resume exists with the given ID.
    - 500 `DATABASE_OPERATION_FAILED`: The edit failed; changes were rolled back.
    """

    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise ResumeNotFoundError(f"No resume found with id {resume_id}")

    if request.item_index < 0 or request.item_index >= len(resume_model.items):
        raise HTTPException(
            status_code=400, detail=f"Invalid item_index {request.item_index}. Out of bounds."
        )

    resume_item = resume_model.items[request.item_index]

    # Copy the bullet points to ensure SQLAlchemy detects the JSON mutation
    updated_bullets = list(resume_item.bullet_points)

    if request.append:
        updated_bullets.append(request.new_content)
    else:
        # Validate bullet_point_index for overwrite
        if request.bullet_point_index is None:
            raise HTTPException(
                status_code=400, detail="bullet_point_index must be provided if not appending."
            )
        if request.bullet_point_index < 0 or request.bullet_point_index >= len(updated_bullets):
            raise HTTPException(
                status_code=400, detail=f"Invalid bullet_point_index {request.bullet_point_index}."
            )

        updated_bullets[request.bullet_point_index] = request.new_content

    try:
        # Apply changes
        resume_item.bullet_points = updated_bullets
        resume_item.last_updated = datetime.datetime.now()
        resume_model.last_updated = datetime.datetime.now()

        session.add(resume_item)
        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return resume_model

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(f"Failed to edit bullet point: {str(e)}") from e


@router.post("/{resume_id}/edit/resume_item", response_model=ResumeResponse)
def edit_resume_item(
    resume_id: int,
    request: EditResumeItemMetadataRequest,  # Corrected request model here
    session=Depends(get_session)
):
    """
    Update the title and date range of a specific resume item.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Body parameters:
    - `item_index`: Zero-based index of the resume item to edit.
    - `start_date`: New start date (YYYY-MM-DD).
    - `end_date`: New end date (YYYY-MM-DD).
    - `title`: New display title.

    Returns:
    - 200: The updated `ResumeResponse`.

    Raises:
    - 400: item_index is out of bounds.
    - 404 `RESUME_NOT_FOUND`: No resume exists with the given ID.
    - 500 `DATABASE_OPERATION_FAILED`: The edit failed; changes were rolled back.
    """

    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise ResumeNotFoundError(f"No resume found with id {resume_id}")

    # Validate item_index bounds
    if request.item_index < 0 or request.item_index >= len(resume_model.items):
        raise HTTPException(
            status_code=400, detail=f"Invalid item_index {request.item_index}. Out of bounds."
        )

    resume_item = resume_model.items[request.item_index]

    try:
        # Apply changes
        if resume_item.title:
            resume_item.title = request.title

        if resume_item:
            resume_item.start_date = request.start_date

        if resume_item:
            resume_item.end_date = request.end_date

        resume_item.last_updated = datetime.datetime.now()
        resume_model.last_updated = datetime.datetime.now()

        session.add(resume_item)
        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return resume_model

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(f"Failed to edit resume item: {str(e)}") from e


@router.post("/{resume_id}/refresh", response_model=ResumeResponse)
def refresh_resume(
    resume_id: int,
    session=Depends(get_session)
):
    """
    Regenerate a resume's content from its current project list.

    Fetches up-to-date project statistics and rebuilds all resume items while
    preserving the existing email and GitHub metadata.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Returns:
    - 200: The refreshed `ResumeResponse`.

    Raises:
    - 400: The resume has no associated projects to refresh from.
    - 404 `RESUME_NOT_FOUND`: No resume exists with the given ID.
    - 404 `PROJECT_NOT_FOUND`: A project associated with this resume no longer exists.
    - 500 `DATABASE_OPERATION_FAILED`: The refresh failed; changes were rolled back.
    """

    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise ResumeNotFoundError(f"No resume found with id {resume_id}")

    project_names = [
        item.project_name for item in resume_model.items if item.project_name]

    if not project_names:
        raise HTTPException(
            status_code=400, detail="Cannot refresh: No projects are associated with this resume."
        )

    project_reports = []
    for project_name in project_names:
        project = get_project_report_by_name(session, project_name)
        if not project:
            raise ProjectNotFoundError(f"No project found with name '{project_name}'")
        project_reports.append(project)

    try:
        user_report = UserReport(
            project_reports=project_reports, report_name="Generated Resume"
        )

        new_resume_domain = user_report.generate_resume(
            email=resume_model.email,
            github=resume_model.github
        )

        updated_model = save_resume(session, new_resume_domain)
        updated_model.id = resume_id
        updated_model.last_updated = datetime.datetime.now()

        session.commit()

        return updated_model

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(f"Failed to refresh resume: {str(e)}") from e
