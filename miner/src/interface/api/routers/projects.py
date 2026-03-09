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
    attributes: List[str] = Field(default_factory=list) #union of selected items
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
    project_model: Optional["ProjectReportModel"],  # or concrete type if imported
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
    frameworks_out = list(project_model.showcase_frameworks) if project_model.showcase_frameworks else default_frameworks
    bullets_out = list(project_model.showcase_bullet_points) if project_model.showcase_bullet_points else default_bullets

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
            missing = sorted(list(wanted_set - {m.project_name for m in models}))
            raise HTTPException(status_code=404, detail=f"Missing project(s): {', '.join(missing)}")
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

        resolved = {a: _resolve_compare_attribute(a, m, report) for a in attributes}

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
    models = [p for p in get_all_project_report_models(session) if p.showcase_selected]
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
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project report {e}")

    if not report:
        raise HTTPException(status_code=404, detail=f"No project report named {project_name}")

    project_model = get_project_report_model_by_name(session, project_name)  
    try:
        return _build_project_showcase_response(project_model, report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build showcase response: {e}")

@router.get("/{project_name}/showcase/customization")
def get_project_showcase_customization(project_name: str, session=Depends(get_session)):
    """
    Returns only the saved customization fields (not the merged showcase output).
    Useful for prefilling an edit form in the UI.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise HTTPException(status_code=404, detail=f"No project report named {project_name}")

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
        raise HTTPException(status_code=404, detail=f"No project report named {project_name}")

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
        raise HTTPException(status_code=500, detail=f"Failed to save showcase customization: {str(e)}")

@router.delete("/{project_name}/showcase/customization")
def clear_project_showcase_customization(project_name: str, session=Depends(get_session)):
    """
    Clear any saved overrides for the showcase view so it falls back to generated defaults.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise HTTPException(status_code=404, detail=f"No project report named {project_name}")

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
        raise HTTPException(status_code=500, detail=f"Failed to clear showcase customization: {str(e)}")

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

@router.put("/representation/reorder")
def reorder_projects(req: ReorderProjectsRequest, session=Depends(get_session)):
    try:
        # validate all exist
        for name in req.project_names:
            if not get_project_report_model_by_name(session, name):
                raise HTTPException(status_code=404, detail=f"No project report named {name}")

        now = datetime.now()
        for idx, name in enumerate(req.project_names):
            m = get_project_report_model_by_name(session, name)
            m.representation_rank = idx
            m.representation_last_user_edit_at = now
            m.last_updated = now
            session.add(m)

        session.commit()
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reorder projects: {str(e)}")

@router.patch("/{project_name}/representation")
def update_project_representation(project_name: str, req: UpdateProjectRepresentationRequest, session=Depends(get_session)):
    m = get_project_report_model_by_name(session, project_name)
    if not m:
        raise HTTPException(status_code=404, detail=f"No project report named {project_name}")

    # validate dates if both provided
    if req.chrono_start_override and req.chrono_end_override:
        if req.chrono_end_override < req.chrono_start_override:
            raise HTTPException(status_code=422, detail="chrono_end_override must be >= chrono_start_override")
        
    if req.representation_rank is not None and req.representation_rank < 0:
        raise HTTPException(status_code=422, detail="representation_rank must be >= 0")

    try:
        if req.representation_rank is not None:
            m.representation_rank = req.representation_rank

        if req.chrono_start_override is not None:
            m.chrono_start_override = req.chrono_start_override
        if req.chrono_end_override is not None:
            m.chrono_end_override = req.chrono_end_override

        if req.showcase_selected is not None:
            m.showcase_selected = req.showcase_selected

        if req.compare_attributes is not None:
            m.compare_attributes = list(req.compare_attributes)

        if req.highlight_skills is not None:
            m.highlight_skills = list(req.highlight_skills)

        now = datetime.now()
        m.representation_last_user_edit_at = now
        m.last_updated = now

        session.add(m)
        session.commit()
        return {"ok": True}

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update representation: {str(e)}")

@router.get("/chronology")
def get_project_chronology(session=Depends(get_session)):
    # uses domain report for start/end from statistics
    projects = get_all_project_report_models(session)

    out = []
    for m in projects:
        report = get_project_report_by_name(session, m.project_name)
        if not report:
            continue
        item = report.generate_resume_item()

        def _to_dt(v):
            if v is None:
                return None
            if isinstance(v, datetime):
                return v
            return datetime.combine(v, datetime.min.time())

        default_start = _to_dt(item.start_date)
        default_end = _to_dt(item.end_date)

        start = m.chrono_start_override or default_start
        end = m.chrono_end_override or default_end

        out.append({
            "project_name": m.project_name,
            "start_date": start,
            "end_date": end,
            "overridden": (m.chrono_start_override is not None or m.chrono_end_override is not None),
        })

    # sort by start_date then end_date
    out.sort(key=lambda x: (x["start_date"] is None, x["start_date"] or datetime.max, x["end_date"] or datetime.max))
    return {"projects": out, "count": len(out)}

def _resolve_compare_attribute(attr: str, project_model, report) -> Any:
    """
    Resolve a compare attribute value for a given project.
    Priority:
    1) If attr is start/end, respect overrides and fallback to report resume item.
    2) frameworks from resume_item
    3) weight from report.get_project_weight (if exists)
    4) fallback: try project_model.statistic[attr]
    """
    # Handle start/end with overrides
    if attr in {"start_date", "end_date"}:
        resume_item = report.generate_resume_item() if report else None

        def _to_dt(v):
            if v is None:
                return None
            if isinstance(v, datetime):
                return v
            return datetime.combine(v, datetime.min.time())

        default_start = _to_dt(getattr(resume_item, "start_date", None)) if resume_item else None
        default_end = _to_dt(getattr(resume_item, "end_date", None)) if resume_item else None

        if attr == "start_date":
            return project_model.chrono_start_override or default_start
        return project_model.chrono_end_override or default_end

    if attr == "frameworks":
        resume_item = report.generate_resume_item() if report else None
        return _frameworks_to_strings(getattr(resume_item, "frameworks", None)) if resume_item else []

    if attr == "weight":
        if report and hasattr(report, "get_project_weight"):
            return report.get_project_weight()
        return None

    # Fallback to statistics dict if present
    try:
        if getattr(project_model, "statistic", None) and attr in project_model.statistic:
            return project_model.statistic[attr]
    except Exception:
        pass

    return None
