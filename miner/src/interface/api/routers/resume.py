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
    items: List[ResumeItemResponse] = []
    created_at: Optional[datetime.datetime]
    last_updated: Optional[datetime.datetime]


# ---------- Resume API Endpoints ----------
@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, session=Depends(get_session)):
    """Retrieve a resume by ID"""

    result = get_resume_model_by_id(session, resume_id)

    if not result:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

    return result


@router.post("/generate", response_model=ResumeResponse)
def generate_resume(request: GenerateResumeRequest, session=Depends(get_session)):
    """Generate a new resume from projects"""

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
            raise HTTPException(
                status_code=404, detail=f"No project found with name '{project_name}'")
        project_reports.append(project)

    try:
        # Generate resume
        user_report = UserReport(
            project_reports=project_reports, report_name="Generated Resume")

        # Extract email and github from user config
        user_email = user_config.user_email if user_config else None
        user_github = user_config.github if user_config else None

        # Generate resume with both email and github
        resume_domain = user_report.generate_resume(user_email, user_github)

        # Save using serialize_resume
        resume_model = save_resume(session, resume_domain)
        session.commit()

        return resume_model

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate resume: {str(e)}")


@router.post("/{resume_id}/edit/metadata", response_model=ResumeResponse)
def edit_resume_metadata(
    resume_id: int,
    request: EditResumeMetadataRequest,
    session=Depends(get_session)
):
    """
    Edit an existing resume. Note, the user config ID is optional. It is not needed
    and will cause an error if used without a corresponding ID.
    """

    # Load as domain object (uses deserialize_resume)

    resume_domain = load_resume(session, resume_id)

    if not resume_domain:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

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
        raise HTTPException(
            status_code=500, detail=f"Failed to edit resume: {str(e)}")


@router.post("/{resume_id}/edit/bullet_point", response_model=ResumeResponse)
def edit_resume_item_bullet_point(
    resume_id: int,
    request: EditBulletPointRequest,
    session=Depends(get_session)
):
    """Edit or append a bullet point to a specific resume item."""

    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

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
        raise HTTPException(
            status_code=500, detail=f"Failed to edit bullet point: {str(e)}")


@router.post("/{resume_id}/edit/resume_item", response_model=ResumeResponse)
def edit_resume_item(
    resume_id: int,
    request: EditResumeItemMetadataRequest,  # Corrected request model here
    session=Depends(get_session)
):
    """Edit the metadata (dates, title) of a specific resume item."""

    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

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
        raise HTTPException(
            status_code=500, detail=f"Failed to edit resume item: {str(e)}")


@router.post("/{resume_id}/refresh", response_model=ResumeResponse)
def refresh_resume(
    resume_id: int,
    session=Depends(get_session)
):
    """
    Refresh a resume with new project information
    """

    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

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
            raise HTTPException(
                status_code=404, detail=f"No project found with name '{project_name}'"
            )
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
        session.refresh(updated_model)

        return updated_model

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh resume: {str(e)}"
        )
