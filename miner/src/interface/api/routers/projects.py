from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import SQLModel, Field
from typing import Optional, List, Any, Dict
from urllib.parse import unquote
from datetime import datetime
import os

from src.interface.api.routers.util import get_session
from src.database.api.CRUD.projects import (
    get_project_report_model_by_name,
    get_project_report_by_name,
    get_all_project_report_models
)
from src.services.mining_service import start_miner_service
from src.database.api.models import UserConfigModel as UserConfig
from src.infrastructure.log.logging import get_logger
from src.database.api.models import ProjectReportModel

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
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frameworks: List[str] = Field(default_factory=list)
    bullet_points: List[str] = Field(default_factory=list)


class ProjectResumeItemResponse(SQLModel):
    title: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frameworks: List[str] = Field(default_factory=list)
    bullet_points: List[str] = Field(default_factory=list)


class SaveShowcaseCustomizationRequest(SQLModel):
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frameworks: Optional[List[str]] = None
    bullet_points: Optional[List[str]] = None


class ReorderProjectsRequest(SQLModel):
    project_names: List[str]  # ordered, index 0 is highest priority


class UpdateProjectRepresentationRequest(SQLModel):
    representation_rank: Optional[int] = None
    chrono_start_override: Optional[datetime] = None
    chrono_end_override: Optional[datetime] = None
    showcase_selected: Optional[bool] = None
    compare_attributes: Optional[List[str]] = None
    highlight_skills: Optional[List[str]] = None


class CompareProjectItem(SQLModel):
    project_name: str
    representation_rank: Optional[int] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class CompareProjectsResponse(SQLModel):
    attributes: List[str] = Field(
        default_factory=list)  # union of selected items
    projects: List[CompareProjectItem] = Field(default_factory=list)
    count: int

# Helper function to polish extracted framework tokens by removing
# URLs, file paths, asset references, and other non-technology noise.


def _clean_framework(value: str) -> Optional[str]:
    if not value:
        return None

    s = value.strip()

    # Drop URLs
    if s.startswith("http://") or s.startswith("https://"):
        return None

    # Drop file paths
    if "/" in s or "\\" in s:
        return None

    # Drop image / asset extensions
    ext = os.path.splitext(s)[1].lower()
    if ext in {".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp"}:
        return None

    # Drop junk tokens
    if len(s) > 40:
        return None

    return s


def _frameworks_to_strings(value: Any) -> List[str]:
    if not value:
        return []

    out: List[str] = []

    for item in value:
        if isinstance(item, str):
            candidate = item
        elif isinstance(item, dict):
            candidate = (
                item.get("name")
                or item.get("skill")
                or item.get("skill_name")
            )
        else:
            candidate = (
                getattr(item, "name", None)
                or getattr(item, "skill", None)
                or getattr(item, "skill_name", None)
            )
        cleaned = _clean_framework(candidate)
        if cleaned:
            out.append(cleaned)

    seen = set()
    deduped: List[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            deduped.append(x)
    return deduped

# Helper function to combine logic of GET/projects{project_name}/showcase and GET /projects/selected


def _build_project_showcase_response(
    # or concrete type if imported
    project_model: Optional["ProjectReportModel"],
    report,
) -> ProjectShowcaseResponse:
    resume_item = report.generate_resume_item()

    def _to_datetime(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.combine(value, datetime.min.time())
        except Exception:
            return None

    # defaults from generator
    default_title = resume_item.title
    default_start = _to_datetime(resume_item.start_date)
    default_end = _to_datetime(resume_item.end_date)
    default_frameworks = _frameworks_to_strings(resume_item.frameworks)
    default_bullets = list(resume_item.bullet_points or [])

    # If no DB model exists, return defaults (no overrides)
    if project_model is None:
        return ProjectShowcaseResponse(
            project_name=report.project_name,
            title=default_title,
            start_date=default_start,
            end_date=default_end,
            frameworks=default_frameworks,
            bullet_points=default_bullets,
        )

    # overrides if present
    title_out = project_model.showcase_title or default_title
    start_out = project_model.showcase_start_date or default_start
    end_out = project_model.showcase_end_date or default_end
    frameworks_out = list(
        project_model.showcase_frameworks) if project_model.showcase_frameworks else default_frameworks
    bullets_out = list(
        project_model.showcase_bullet_points) if project_model.showcase_bullet_points else default_bullets

    # chronology overrides respected (“last bullet”)
    if project_model.chrono_start_override is not None:
        start_out = project_model.chrono_start_override
    if project_model.chrono_end_override is not None:
        end_out = project_model.chrono_end_override

    return ProjectShowcaseResponse(
        project_name=report.project_name,
        title=title_out,
        start_date=start_out,
        end_date=end_out,
        frameworks=frameworks_out,
        bullet_points=bullets_out,
    )


@router.post("/upload", response_model=UploadProjectResponse)
def upload_project(
    file: UploadFile = File(...),
    email: Optional[str] = None,
    portfolio_name: Optional[str] = None,
    session=Depends(get_session)
):
    """
    POST /upload

    This endpoint will intake a zipped file. This zipped file will then
    be analyzed for projects. These projects will be analyzed, then saved
    to the database.

    Errors will be thrown if the zipped file does not match the accepted formats.
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve the list of projects from the database: {type(e).__name__}: {str(e)}"
        )


def _resolve_compare_attribute(attr: str, model, report) -> Any:
    """Resolve a single compare attribute to its display value."""
    resume_item = report.generate_resume_item()

    def _to_dt(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.combine(value, datetime.min.time())
        except Exception:
            return None

    if attr == "start_date":
        if model.chrono_start_override is not None:
            return model.chrono_start_override
        return _to_dt(resume_item.start_date)

    if attr == "end_date":
        if model.chrono_end_override is not None:
            return model.chrono_end_override
        return _to_dt(resume_item.end_date)

    if attr == "frameworks":
        return _frameworks_to_strings(resume_item.frameworks)

    if attr == "weight":
        return report.get_project_weight()

    return getattr(resume_item, attr, None)


@router.get("/compare", response_model=CompareProjectsResponse)
def compare_projects(projects: Optional[str] = None, session=Depends(get_session)):
    """
    Compare projects using saved compare_attributes.
    Query param: ?projects=A,B,C
    If not provided, compares all projects that have any compare_attributes selected.
    """
    project_reports = get_all_project_report_models(session)

    # Filter target set
    if projects:
        wanted = [unquote(x.strip()) for x in projects.split(",") if x.strip()]
        wanted_set = set(wanted)
        models = [m for m in project_reports if m.project_name in wanted_set]

        if len(models) != len(wanted_set):
            missing = sorted(
                list(wanted_set - {m.project_name for m in models}))
            raise HTTPException(
                status_code=404, detail=f"Missing project(s): {', '.join(missing)}")
    else:
        models = [m for m in project_reports if (m.compare_attributes or [])]

    # Determine union of attributes (stable order)
    attr_set = set()
    for m in models:
        for a in (m.compare_attributes or []):
            attr_set.add(a)

    attributes = sorted(attr_set)

    # Sort projects
    models.sort(
        key=lambda p: (
            p.representation_rank is None,
            p.representation_rank if p.representation_rank is not None else 10**9,
            p.created_at,
        )
    )

    out_projects: List[CompareProjectItem] = []
    for m in models:
        report = get_project_report_by_name(session, m.project_name)

        resolved = {a: _resolve_compare_attribute(
            a, m, report) for a in attributes}

        out_projects.append(
            CompareProjectItem(
                project_name=m.project_name,
                representation_rank=m.representation_rank,
                attributes=resolved,
            )
        )

    return CompareProjectsResponse(
        attributes=attributes,
        projects=out_projects,
        count=len(out_projects),
    )


@router.get("/showcase/selected")
def get_selected_showcase_projects(session=Depends(get_session)):
    """
    Return all projects marked showcase_selected=True, ordered by representation_rank.
    Each project is returned in the same merged format as GET /projects/{name}/showcase.
    """
    models = [p for p in get_all_project_report_models(
        session) if p.showcase_selected]
    models.sort(
        key=lambda p: (
            p.representation_rank is None,
            p.representation_rank if p.representation_rank is not None else 10**9,
            p.created_at,
        )
    )

    out = []
    for m in models:
        report = get_project_report_by_name(session, m.project_name)
        if not report:
            continue
        out.append(_build_project_showcase_response(m, report))

    return {"projects": out, "count": len(out)}


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
            status_code=500, detail=f"Failed to retrieve project report {e}")

    if not report:
        raise HTTPException(
            status_code=404, detail=f"No project report named {project_name}")

    resume_item = report.generate_resume_item()
    project_model = get_project_report_model_by_name(session, project_name)

    # Helper to normalize date → datetime
    def _to_datetime(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.combine(value, datetime.min.time())
        except Exception as e:
            logger.warning(
                "Failed to convert value '%s' to datetime in project endpoint: %s",
                value,
                str(e),
            )
            return None

    # Default generated fields
    default_title = resume_item.title
    default_start = _to_datetime(resume_item.start_date)
    default_end = _to_datetime(resume_item.end_date)
    default_frameworks = _frameworks_to_strings(resume_item.frameworks)
    default_bullets = list(resume_item.bullet_points or [])

    # Apply overrides
    title_out = (
        project_model.showcase_title
        if (project_model and project_model.showcase_title)
        else default_title
    )

    start_out = project_model.showcase_start_date if (
        project_model and project_model.showcase_start_date) else default_start
    end_out = project_model.showcase_end_date if (
        project_model and project_model.showcase_end_date) else default_end

    # Chronology overrides take highest priority
    if project_model and project_model.chrono_start_override is not None:
        start_out = project_model.chrono_start_override
    if project_model and project_model.chrono_end_override is not None:
        end_out = project_model.chrono_end_override

    frameworks_out = (
        list(project_model.showcase_frameworks)
        if (project_model and project_model.showcase_frameworks)
        else default_frameworks
    )
    bullets_out = (
        list(project_model.showcase_bullet_points)
        if (project_model and project_model.showcase_bullet_points)
        else default_bullets
    )

    return ProjectShowcaseResponse(
        project_name=report.project_name,
        title=title_out,
        start_date=start_out,
        end_date=end_out,
        frameworks=frameworks_out,
        bullet_points=bullets_out,
    )


@router.get("/{project_name}/showcase/customization")
def get_project_showcase_customization(project_name: str, session=Depends(get_session)):
    """
    Returns only the saved customization fields (not the merged showcase output).
    Useful for prefilling an edit form in the UI.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise HTTPException(
            status_code=404, detail=f"No project report named {project_name}")

    return {
        "project_name": project_model.project_name,
        "title": project_model.showcase_title,
        "start_date": project_model.showcase_start_date,
        "end_date": project_model.showcase_end_date,
        "frameworks": list(project_model.showcase_frameworks or []),
        "bullet_points": list(project_model.showcase_bullet_points or []),
        "last_user_edit_at": project_model.showcase_last_user_edit_at,
    }


@router.put("/{project_name}/showcase/customization")
def save_project_showcase_customization(
    project_name: str,
    request: SaveShowcaseCustomizationRequest,
    session=Depends(get_session),
):
    """
    Persist user overrides for the portfolio showcase view of a project.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise HTTPException(
            status_code=404, detail=f"No project report named {project_name}")

    try:
        if request.title is not None:
            project_model.showcase_title = request.title

        if request.start_date is not None:
            project_model.showcase_start_date = request.start_date

        if request.end_date is not None:
            project_model.showcase_end_date = request.end_date

        if request.frameworks is not None:
            project_model.showcase_frameworks = list(request.frameworks)

        if request.bullet_points is not None:
            project_model.showcase_bullet_points = list(request.bullet_points)

        project_model.showcase_last_user_edit_at = datetime.now()
        project_model.last_updated = datetime.now()

        session.add(project_model)
        session.commit()
        session.refresh(project_model)

        return {"ok": True}

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to save showcase customization: {str(e)}")


@router.delete("/{project_name}/showcase/customization")
def clear_project_showcase_customization(project_name: str, session=Depends(get_session)):
    """
    Clear any saved overrides for the showcase view so it falls back to generated defaults.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise HTTPException(
            status_code=404, detail=f"No project report named {project_name}")

    try:
        project_model.showcase_title = None
        project_model.showcase_start_date = None
        project_model.showcase_end_date = None
        project_model.showcase_frameworks = []
        project_model.showcase_bullet_points = []
        project_model.showcase_last_user_edit_at = None
        project_model.last_updated = datetime.now()

        session.add(project_model)
        session.commit()

        return {"ok": True}

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to clear showcase customization: {str(e)}")


@router.get("/{project_name}/resume-item", response_model=ProjectResumeItemResponse)
def get_project_resume_item(project_name: str, session=Depends(get_session)):
    """
    GET /{project_name}/resume-item

    This endpoint will retrieve a passed in project_name and format it
    as a résumé item. The idea is that a user can select which project
    they would like to include in their résumé through the UI, and the
    system will call this endpoint to generate a structured résumé entry
    for that project.

    Returns the project formatted as a résumé item, including title,
    date range, frameworks used, and descriptive bullet points.
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

    def _to_datetime(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.combine(value, datetime.min.time())
        except Exception as e:
            logger.warning(
                "Failed to convert value '%s' to datetime in project endpoint: %s",
                value,
                str(e),
            )
            return None

    return ProjectResumeItemResponse(
        title=resume_item.title,
        start_date=_to_datetime(resume_item.start_date),
        end_date=_to_datetime(resume_item.end_date),
        frameworks=_frameworks_to_strings(resume_item.frameworks),
        bullet_points=list(resume_item.bullet_points or []),
    )


@router.post("/{project_name}/image")
def upload_project_image(
    project_name: str,
    file: UploadFile = File(...),
    session=Depends(get_session)
):
    """
    POST /{project_name}/image

    Uploads an image file and assigns it to the specified project.
    Validates that the uploaded file is an image before saving.
    """

    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise HTTPException(
            status_code=404,
            detail=f"No project report named {project_name}"
        )

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
        project_model.last_updated = datetime.now()

        session.add(project_model)
        session.commit()

        return {"message": f"Image successfully assigned to project '{project_name}'."}

    except Exception as e:
        session.rollback()
        logger.error("Error uploading image for project %s: %s",
                     project_name, str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image."
        )


@router.put("/representation/reorder")
def reorder_projects(request: ReorderProjectsRequest, session=Depends(get_session)):
    """
    Assign representation_rank to each project in the given order.
    Index 0 gets rank 0 (highest priority).
    """
    try:
        for rank, project_name in enumerate(request.project_names):
            model = get_project_report_model_by_name(session, project_name)
            if model is None:
                raise HTTPException(
                    status_code=404, detail=f"No project report named {project_name}")
            model.representation_rank = rank
            session.add(model)
        session.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to reorder projects: {str(e)}")


@router.patch("/{project_name}/representation")
def update_project_representation(
    project_name: str,
    request: UpdateProjectRepresentationRequest,
    session=Depends(get_session),
):
    """Update representation metadata for a project."""
    model = get_project_report_model_by_name(session, project_name)
    if not model:
        raise HTTPException(
            status_code=404, detail=f"No project report named {project_name}")

    if request.representation_rank is not None and request.representation_rank < 0:
        raise HTTPException(
            status_code=422, detail="representation_rank must be >= 0")

    if request.chrono_start_override is not None and request.chrono_end_override is not None:
        if request.chrono_end_override < request.chrono_start_override:
            raise HTTPException(
                status_code=422,
                detail="chrono_end_override must be >= chrono_start_override")

    try:
        if request.representation_rank is not None:
            model.representation_rank = request.representation_rank
        if request.chrono_start_override is not None:
            model.chrono_start_override = request.chrono_start_override
        if request.chrono_end_override is not None:
            model.chrono_end_override = request.chrono_end_override
        if request.showcase_selected is not None:
            model.showcase_selected = request.showcase_selected
        if request.compare_attributes is not None:
            model.compare_attributes = list(request.compare_attributes)
        if request.highlight_skills is not None:
            model.highlight_skills = list(request.highlight_skills)

        model.last_updated = datetime.now()
        session.add(model)
        session.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update representation: {str(e)}")
