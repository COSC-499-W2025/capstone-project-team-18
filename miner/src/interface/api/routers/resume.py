from fastapi import APIRouter,  Depends, HTTPException
from sqlmodel import SQLModel
from typing import List, Optional
from datetime import datetime, date

from src.interface.api.routers.util import get_session
from src.interface.api.routers.user_config import get_user_config_safe
from src.database import (
    ResumeModel,
    ResumeItemModel,
    UserConfigModel,
    get_project_report_by_name
)
from src.database.api.CRUD.resume import save_resume, load_resume, get_resume_model_by_id
from src.core.report.user.user_report import UserReport

router = APIRouter(
    prefix="/resume",
    tags=["resume"],
)

# ---------- Request/Response Models ----------
class GenerateResumeRequest(SQLModel):
    """Request model for generating a resume"""
    project_names: List[str]
    user_config_id: Optional[int] = None

class EditResumeRequest(SQLModel):
    """Request model for editing a resume"""
    email: Optional[str] = None

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
    created_at: Optional[datetime]
    last_updated: Optional[datetime]


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


@router.post("/{resume_id}/edit", response_model=ResumeResponse)
def edit_resume(
    resume_id: int,
    request: EditResumeRequest,
    session=Depends(get_session)
):
    """Edit an existing resume."""

    # Load as domain object (uses deserialize_resume)

    resume_domain = load_resume(session, resume_id)

    if not resume_domain:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

    try:
        # Update fields
        if request.email is not None:
            resume_domain.email = request.email

        # Save updated (uses serialize_resume)
        updated_model = save_resume(session, resume_domain)
        updated_model.id = resume_id

        session.commit()

        return updated_model

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to edit resume: {str(e)}")
