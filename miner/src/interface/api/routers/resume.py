from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import SQLModel
from typing import List, Optional
import datetime

from src.interface.api.routers.util import get_session
from src.interface.api.routers.user_config import get_user_config_safe
import src.database as _db
from src.database import (
    get_project_report_by_name,
)
from src.database.api.CRUD.resume import (
    save_resume,
    load_resume,
    get_resume_model_by_id,
    list_resumes,
    delete_resume,
)
from src.core.report.user.user_report import UserReport
from src.core.statistic.user_stat_collection import UserStatCollection
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
    title: Optional[str] = None


class EditResumeMetadataRequest(SQLModel):
    """Request model for editing a resume"""
    title: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    github_username: Optional[str] = None
    linkedin: Optional[str] = None


class EditBulletPointRequest(SQLModel):
    resume_id: int
    item_index: int
    new_content: str

    # Are we adding a new bullet?
    append: bool

    # If not appending, need what index we are overwritting
    bullet_point_index: Optional[int] = None


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


class SkillsByExpertiseResponse(SQLModel):
    """Categorized skills by expertise level"""
    expert: List[str] = []
    intermediate: List[str] = []
    exposure: List[str] = []


class EducationEntry(SQLModel):
    """A single structured education entry with optional date range."""
    title: str
    start: Optional[str] = None
    end: Optional[str] = None


class AwardEntry(SQLModel):
    """A single structured award entry with optional date range."""
    title: str
    start: Optional[str] = None
    end: Optional[str] = None


def _normalize_entry(entry) -> dict:
    """Normalize a legacy plain-string entry or a structured dict into {title, start, end}."""
    if isinstance(entry, dict):
        return {"title": entry.get("title", ""), "start": entry.get("start"), "end": entry.get("end")}
    return {"title": str(entry), "start": None, "end": None}


class ResumeResponse(SQLModel):
    """Response model for a resume with items"""
    id: Optional[int] = None
    title: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    skills: List[str]
    skills_by_expertise: Optional[SkillsByExpertiseResponse] = None
    education: List[EducationEntry] = []
    awards: List[AwardEntry] = []
    items: List[ResumeItemResponse] = []
    created_at: Optional[datetime.datetime]
    last_updated: Optional[datetime.datetime]


class ResumeListItemResponse(SQLModel):
    """Lightweight response model for listing produced resumes"""
    id: int
    title: Optional[str] = None
    email: Optional[str] = None
    github: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    last_updated: Optional[datetime.datetime] = None
    item_count: int = 0
    project_names: List[str] = []


class ResumeListResponse(SQLModel):
    """Response model for all produced resumes"""
    resumes: List[ResumeListItemResponse]
    count: int

# Helper function.


def _build_resume_response(resume_model) -> ResumeResponse:
    """
    Build a ResumeResponse using per-resume education/awards snapshots.
    """
    education = [EducationEntry(**_normalize_entry(e))
                 for e in (resume_model.education or [])]
    awards = [AwardEntry(**_normalize_entry(a))
              for a in (resume_model.awards or [])]

    expert = resume_model.skills_expert or []
    intermediate = resume_model.skills_intermediate or []
    exposure = resume_model.skills_exposure or []
    if expert or intermediate or exposure:
        skills_by_expertise = SkillsByExpertiseResponse(
            expert=expert,
            intermediate=intermediate,
            exposure=exposure,
        )
    else:
        skills_by_expertise = None

    return ResumeResponse(
        id=resume_model.id,
        title=resume_model.title,
        name=resume_model.name,
        location=resume_model.location,
        email=resume_model.email,
        github=resume_model.github,
        linkedin=resume_model.linkedin,
        skills=resume_model.skills,
        skills_by_expertise=skills_by_expertise,
        education=education,
        awards=awards,
        items=resume_model.items,
        created_at=resume_model.created_at,
        last_updated=resume_model.last_updated,
    )


def _build_resume_list_item(resume_model) -> ResumeListItemResponse:
    """
    Build a lightweight response object for the resume list page.
    """
    project_names = [
        item.project_name for item in (resume_model.items or [])
        if item.project_name
    ]
    return ResumeListItemResponse(
        id=resume_model.id,
        title=resume_model.title,
        email=resume_model.email,
        github=resume_model.github,
        created_at=resume_model.created_at,
        last_updated=resume_model.last_updated,
        item_count=len(resume_model.items or []),
        project_names=project_names,
    )


class EditSkillsRequest(SQLModel):
    """Request model for editing categorized skills"""
    expert: List[str]
    intermediate: List[str]
    exposure: List[str]


class DeleteBulletPointRequest(SQLModel):
    """Request model for deleting a bullet point"""
    item_index: int
    bullet_point_index: int


class EditFrameworksRequest(SQLModel):
    """Request model for editing frameworks for a resume item"""
    item_index: int
    frameworks: List[str]


class EditEducationRequest(SQLModel):
    """Request model for replacing the education list on a resume"""
    education: List[EducationEntry]


class EditAwardsRequest(SQLModel):
    """Request model for replacing the awards list on a resume"""
    awards: List[AwardEntry]


# ---------- Resume API Endpoints ----------

@router.get("", response_model=ResumeListResponse)
def get_all_resumes(session=Depends(get_session)):
    """
    GET /resume

    Returns a lightweight list of all produced resumes.
    Each entry contains: id, email, github, created_at, last_updated, item_count.
    """
    resume_models = list_resumes(session)
    resumes = [_build_resume_list_item(resume_model)
               for resume_model in resume_models]

    return ResumeListResponse(
        resumes=resumes,
        count=len(resumes),
    )


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

    # If no stored skills, try to calculate from UserReport
    has_stored_skills = (
        bool(result.skills_expert) or
        bool(result.skills_intermediate) or
        bool(result.skills_exposure)
    )
    if not has_stored_skills:
        user_config = _db.get_most_recent_user_config(session)
        if user_config and user_config.project_reports:
            try:
                project_reports = [
                    get_project_report_by_name(session, p.project_name)
                    for p in user_config.project_reports
                ]
                project_reports = [p for p in project_reports if p is not None]
                if project_reports:
                    report = UserReport(project_reports)
                    weighted_skills = report.statistics.get_value(
                        UserStatCollection.USER_SKILLS.value) or []
                    expert, intermediate, exposure = [], [], []
                    for ws in weighted_skills:
                        if ws.weight >= 0.7:
                            expert.append(ws.skill_name)
                        elif ws.weight >= 0.4:
                            intermediate.append(ws.skill_name)
                        else:
                            exposure.append(ws.skill_name)
                    result.skills_expert = expert
                    result.skills_intermediate = intermediate
                    result.skills_exposure = exposure
            except Exception:
                pass

    return _build_resume_response(result)


@router.post("/{resume_id}/edit/skills", response_model=ResumeResponse)
def edit_resume_skills(
    resume_id: int,
    request: EditSkillsRequest,
    session=Depends(get_session)
):
    """Edit categorized skills for a resume"""
    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise HTTPException(
            status_code=404,
            detail=f"No resume found with id {resume_id}"
        )

    try:
        from sqlalchemy.orm.attributes import flag_modified

        # Update categorized skills
        resume_model.skills_expert = list(request.expert)
        resume_model.skills_intermediate = list(request.intermediate)
        resume_model.skills_exposure = list(request.exposure)

        # Update flat skills list
        resume_model.skills = list(
            request.expert) + list(request.intermediate) + list(request.exposure)

        flag_modified(resume_model, "skills_expert")
        flag_modified(resume_model, "skills_intermediate")
        flag_modified(resume_model, "skills_exposure")
        flag_modified(resume_model, "skills")

        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to edit skills: {str(e)}"
        )


@router.post("/{resume_id}/edit/education", response_model=ResumeResponse)
def edit_resume_education(
    resume_id: int,
    request: EditEducationRequest,
    session=Depends(get_session)
):
    """Replace the education list for a resume."""
    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise HTTPException(
            status_code=404,
            detail=f"No resume found with id {resume_id}"
        )

    try:
        resume_model.education = [e.model_dump() for e in request.education]
        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to edit education: {str(e)}"
        )


@router.post("/{resume_id}/edit/awards", response_model=ResumeResponse)
def edit_resume_awards(
    resume_id: int,
    request: EditAwardsRequest,
    session=Depends(get_session)
):
    """Replace the awards list for a resume."""
    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise HTTPException(
            status_code=404,
            detail=f"No resume found with id {resume_id}"
        )

    try:
        resume_model.awards = [a.model_dump() for a in request.awards]
        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to edit awards: {str(e)}"
        )


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
            raise ProjectNotFoundError(
                f"No project found with name '{project_name}'")
        project_reports.append(project)

    try:
        # Generate resume
        user_report = UserReport(
            project_reports=project_reports, report_name="Generated Resume")

        # Extract defaults from user config
        user_email = user_config.user_email if user_config else None
        user_github = user_config.github if user_config else None
        user_name = user_config.name if user_config else None

        # Extract education/awards from ResumeConfigModel
        user_education = []
        user_awards = []
        if user_config and user_config.resume_config:
            user_education = user_config.resume_config.education or []
            user_awards = user_config.resume_config.awards or []

        # Generate resume with email, github, name, education and awards
        resume_domain = user_report.generate_resume(
            user_email,
            user_github,
            education=user_education,
            awards=user_awards,
            name=user_name,
        )

        # Save using serialize_resume
        resume_model = save_resume(session, resume_domain)

        # Apply optional title after save
        if request.title:
            resume_model.title = request.title.strip() or None
        session.commit()

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to generate resume: {str(e)}") from e


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
    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

    try:
        if request.title is not None:
            resume_model.title = request.title.strip() or None

        if request.name is not None:
            resume_model.name = request.name.strip() or None

        if request.location is not None:
            resume_model.location = request.location.strip() or None

        if request.email is not None:
            resume_model.email = request.email

        if request.github_username is not None:
            resume_model.github = request.github_username

        if request.linkedin is not None:
            resume_model.linkedin = request.linkedin.strip() or None

        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

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
        resume_item.last_updated = datetime.datetime.now(datetime.timezone.utc)
        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_item)
        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to edit bullet point: {str(e)}") from e


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

        resume_item.last_updated = datetime.datetime.now(datetime.timezone.utc)
        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_item)
        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to edit resume item: {str(e)}") from e


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
            raise ProjectNotFoundError(
                f"No project found with name '{project_name}'")
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
        updated_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.commit()

        return _build_resume_response(updated_model)

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to refresh resume: {str(e)}") from e


@router.post("/{resume_id}/edit/bullet_point/delete", response_model=ResumeResponse)
def delete_resume_item_bullet_point(
    resume_id: int,
    request: DeleteBulletPointRequest,
    session=Depends(get_session)
):
    """
    Delete a bullet point from a specific resume item.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Body parameters:
    - `item_index`: Zero-based index of the resume item.
    - `bullet_point_index`: Zero-based index of the bullet point to delete.

    Returns:
    - 200: The updated `ResumeResponse`.

    Raises:
    - 400: item_index or bullet_point_index is out of bounds.
    - 404 `RESUME_NOT_FOUND`: No resume exists with the given ID.
    - 500 `DATABASE_OPERATION_FAILED`: The delete failed; changes were rolled back.
    """

    resume_model = get_resume_model_by_id(session, resume_id)

    if not resume_model:
        raise ResumeNotFoundError(f"No resume found with id {resume_id}")

    if request.item_index < 0 or request.item_index >= len(resume_model.items):
        raise HTTPException(
            status_code=400, detail=f"Invalid item_index {request.item_index}. Out of bounds."
        )

    resume_item = resume_model.items[request.item_index]
    updated_bullets = list(resume_item.bullet_points)

    if request.bullet_point_index < 0 or request.bullet_point_index >= len(updated_bullets):
        raise HTTPException(
            status_code=400, detail=f"Invalid bullet_point_index {request.bullet_point_index}. Out of bounds."
        )

    try:
        updated_bullets.pop(request.bullet_point_index)
        resume_item.bullet_points = updated_bullets
        resume_item.last_updated = datetime.datetime.now(datetime.timezone.utc)
        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_item)
        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to delete bullet point: {str(e)}") from e


@router.post("/{resume_id}/edit/frameworks", response_model=ResumeResponse)
def edit_resume_item_frameworks(
    resume_id: int,
    request: EditFrameworksRequest,
    session=Depends(get_session)
):
    """
    Replace the frameworks list for a specific resume item.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Body parameters:
    - `item_index`: Zero-based index of the resume item to edit.
    - `frameworks`: New list of framework/technology names.

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

    if request.item_index < 0 or request.item_index >= len(resume_model.items):
        raise HTTPException(
            status_code=400, detail=f"Invalid item_index {request.item_index}. Out of bounds."
        )

    resume_item = resume_model.items[request.item_index]

    try:
        resume_item.frameworks = list(request.frameworks)
        resume_item.last_updated = datetime.datetime.now(datetime.timezone.utc)
        resume_model.last_updated = datetime.datetime.now(
            datetime.timezone.utc)

        session.add(resume_item)
        session.add(resume_model)
        session.commit()
        session.refresh(resume_model)

        return _build_resume_response(resume_model)

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to edit frameworks: {str(e)}") from e


@router.get("/{resume_id}/export/pdf")
def export_resume_pdf(resume_id: int, session=Depends(get_session)):
    """
    Export a resume as a PDF file.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Returns:
    - 200: PDF file as an attachment.

    Raises:
    - 404: No resume exists with the given ID.
    - 500: PDF rendering failed (e.g. pdflatex not installed).
    """
    from src.core.resume.render import PDFRenderer

    resume = load_resume(session, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=404,
            detail=f"No resume found with id {resume_id}"
        )

    try:
        pdf_bytes = PDFRenderer().render(resume)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF rendering error: {str(e)}"
        )

    if not pdf_bytes:
        raise HTTPException(
            status_code=500,
            detail="PDF rendering produced empty output. Ensure pdflatex is installed and the LaTeX source is valid."
        )

    filename = f"{resume.title or f'resume_{resume_id}'}.pdf"
    filename = "".join(c for c in filename if c.isalnum()
                       or c in ("-", "_", ".")).strip()
    if not filename:
        filename = f"resume_{resume_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{resume_id}/export/docx")
def export_resume_docx(resume_id: int, session=Depends(get_session)):
    """Export a resume as a Word (.docx) file."""
    from src.core.resume.render import DocxResumeRenderer

    resume = load_resume(session, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=404, detail=f"No resume found with id {resume_id}")

    try:
        docx_bytes = DocxResumeRenderer().render(resume)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Word export error: {str(e)}")

    filename = f"{resume.title or f'resume_{resume_id}'}.docx"
    filename = "".join(c for c in filename if c.isalnum() or c in (
        "-", "_", ".")).strip() or f"resume_{resume_id}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{resume_id}", status_code=200)
def delete_resume_endpoint(
    resume_id: int,
    session=Depends(get_session)
):
    """
    Delete a resume and all its items by ID.

    Path parameters:
    - `resume_id`: Integer primary key of the resume record.

    Returns:
    - 200: `{"message": "Resume deleted."}` on success.

    Raises:
    - 404 `RESUME_NOT_FOUND`: No resume exists with the given ID.
    - 500 `DATABASE_OPERATION_FAILED`: Deletion failed; changes were rolled back.
    """
    try:
        deleted = delete_resume(session, resume_id)
        if not deleted:
            raise ResumeNotFoundError(f"No resume found with id {resume_id}")
        session.commit()
        return {"message": "Resume deleted."}
    except ResumeNotFoundError:
        raise
    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to delete resume: {str(e)}") from e
