import base64
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import field_serializer
from sqlmodel import Field, SQLModel
from src.database.api.CRUD.projects import (get_all_project_report_models,
                                            get_project_report_by_name,
                                            get_project_report_model_by_name,
                                            soft_delete_project_report_by_name)
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
    session=Depends(get_session)
):
    """
    Ingest a compressed project archive, analyze its contents, and persist the results.

    Supported archive formats: .tar.gz, .gz, .7z, .zip.

    The saved UserConfig (email, github, consent) is loaded from the database
    and passed to the miner, so all persisted settings are used during mining.


    Query parameters:
    - `email`: Optional user email to associate with the analysis.
    - `portfolio_name`: Optional name to assign to the portfolio; derived from the
      filename if omitted.

    Form parameters:
    - `file`: The compressed archive to analyze.

    Returns:
    - 200: An `UploadProjectResponse` with a confirmation message and portfolio name.

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
    Compare selected projects across their saved comparison attributes.

    Query parameters:
    - `projects`: Optional comma-separated project names. When omitted, all projects
      that have any compare_attributes set are included.

    Returns:
    - 200: A `CompareProjectsResponse` with the union of attributes and per-project
      attribute values.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: One or more named projects were not found in the database.
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
            raise ProjectNotFoundError(
                f"Missing project(s): {', '.join(missing)}")
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
    Return all projects flagged as showcase_selected=True, ordered by representation_rank.

    Each project is returned in the merged showcase format (generated defaults combined
    with user overrides).

    Returns:
    - 200: `{"projects": [...], "count": N}` with a list of `ProjectShowcaseResponse` objects.
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


@router.get("/{project_name}/showcase", response_model=ProjectShowcaseResponse)
def get_project_showcase(project_name: str, session=Depends(get_session)):
    """
    Return the merged showcase view for a project, combining AI-generated defaults
    with any saved user overrides.

    Path parameters:
    - `project_name`: The unique name of the project.

    Returns:
    - 200: A `ProjectShowcaseResponse` with title, date range, frameworks, and bullet points.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: An unexpected error occurred while fetching the report.
    """
    try:
        report = get_project_report_by_name(session, project_name)
    except Exception as e:
        raise DatabaseOperationError(
            f"Failed to retrieve project report: {e}") from e

    if not report:
        raise ProjectNotFoundError(f"No project report named {project_name}")

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
    Return only the saved user-override fields for a project's showcase view.

    Useful for pre-populating an edit form in the UI without applying generated defaults.

    Path parameters:
    - `project_name`: The unique name of the project.

    Returns:
    - 200: An object with `project_name`, `title`, `start_date`, `end_date`, `frameworks`,
      `bullet_points`, and `last_user_edit_at`.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise ProjectNotFoundError(f"No project report named {project_name}")

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
    Persist user-defined overrides for the portfolio showcase view of a project.

    All fields are optional; only provided fields are updated.

    Path parameters:
    - `project_name`: The unique name of the project.

    Body parameters:
    - `title`: Optional display title override.
    - `start_date`: Optional start date override (ISO 8601).
    - `end_date`: Optional end date override (ISO 8601).
    - `frameworks`: Optional list of technology names to display.
    - `bullet_points`: Optional list of bullet point strings.

    Returns:
    - 200: `{"ok": true}` on success.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: The save operation failed; changes were rolled back.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise ProjectNotFoundError(f"No project report named {project_name}")

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

        project_model.showcase_last_user_edit_at = datetime.now(timezone.utc)
        project_model.last_updated = datetime.now(timezone.utc)

        session.add(project_model)
        session.commit()
        session.refresh(project_model)

        return {"ok": True}

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to save showcase customization: {str(e)}") from e


@router.delete("/{project_name}/showcase/customization")
def clear_project_showcase_customization(project_name: str, session=Depends(get_session)):
    """
    Remove all user-defined overrides for a project's showcase view, reverting it to
    generated defaults.

    Path parameters:
    - `project_name`: The unique name of the project.

    Returns:
    - 200: `{"ok": true}` on success.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: The clear operation failed; changes were rolled back.
    """
    project_model = get_project_report_model_by_name(session, project_name)
    if not project_model:
        raise ProjectNotFoundError(f"No project report named {project_name}")

    try:
        project_model.showcase_title = None
        project_model.showcase_start_date = None
        project_model.showcase_end_date = None
        project_model.showcase_frameworks = []
        project_model.showcase_bullet_points = []
        project_model.showcase_last_user_edit_at = None
        project_model.last_updated = datetime.now(timezone.utc)

        session.add(project_model)
        session.commit()

        return {"ok": True}

    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to clear showcase customization: {str(e)}") from e


@router.get("/{project_name}/resume-item", response_model=ProjectResumeItemResponse)
def get_project_resume_item(project_name: str, session=Depends(get_session)):
    """
    Format a project as a structured résumé entry.

    Generates a title, date range, frameworks, and descriptive bullet points
    from the project's mined statistics.

    Path parameters:
    - `project_name`: The unique name of the project.

    Returns:
    - 200: A `ProjectResumeItemResponse` ready for embedding in a résumé.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: An unexpected error occurred while fetching the report.
    """
    try:
        report = get_project_report_by_name(session, project_name)
    except Exception as e:
        raise DatabaseOperationError(
            f"Failed to retrieve project report: {e}") from e

    if not report:
        raise ProjectNotFoundError(f"No project report named {project_name}")

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


@router.delete(
    "/{project_name}",
    status_code=204,
    summary="Soft-delete a project",
    responses={
        204: {"description": "Project successfully soft-deleted (no content)"},
        404: {"description": "PROJECT_NOT_FOUND — no project with that name exists"},
        500: {"description": "DATABASE_OPERATION_FAILED — deletion failed; changes were rolled back"},
    },
)
def delete_project(
    project_name: str,
    session=Depends(get_session),
):
    """
    Soft-delete a project by name.

    The project record is retained in the database so that existing resumes
    and portfolios can continue to reference it. The project will no longer
    appear in the project list or be available for new resume/portfolio creation.
    Re-uploading a zip with the same project name will resurrect the project.

    Path parameters:
    - `project_name`: The URL-encoded name of the project to delete.

    Returns:
    - 204: No content on success.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project exists with the given name.
    - 500 `DATABASE_OPERATION_FAILED`: The deletion failed; changes were rolled back.
    """
    decoded = unquote(project_name)
    try:
        deleted = soft_delete_project_report_by_name(session, decoded)
        if not deleted:
            raise ProjectNotFoundError(f"No project report named '{decoded}'")
        session.commit()

    except ProjectNotFoundError:
        raise

    except Exception as e:
        session.rollback()
        logger.error("Error soft-deleting project %s: %s", decoded, str(e))
        raise DatabaseOperationError(
            f"Failed to delete project: {str(e)}") from e


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


@router.put("/representation/reorder")
def reorder_projects(request: ReorderProjectsRequest, session=Depends(get_session)):
    """
    Assign representation_rank values to projects in the specified order.

    The first project in the list receives rank 0 (highest priority).

    Body parameters:
    - `project_names`: An ordered list of project names.

    Returns:
    - 200: `{"ok": true}` on success.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: A project name in the list does not exist in the database.
    - 500 `DATABASE_OPERATION_FAILED`: The reorder operation failed; changes were rolled back.
    """
    try:
        for rank, project_name in enumerate(request.project_names):
            model = get_project_report_model_by_name(session, project_name)
            if model is None:
                raise ProjectNotFoundError(
                    f"No project report named {project_name}")
            model.representation_rank = rank
            session.add(model)
        session.commit()
        return {"ok": True}
    except ProjectNotFoundError:
        raise
    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to reorder projects: {str(e)}") from e


@router.patch("/{project_name}/representation")
def update_project_representation(
    project_name: str,
    request: UpdateProjectRepresentationRequest,
    session=Depends(get_session),
):
    """
    Update representation metadata fields for a specific project.

    All body fields are optional; only provided fields are updated.

    Path parameters:
    - `project_name`: The unique name of the project.

    Body parameters:
    - `representation_rank`: Optional integer rank (must be >= 0).
    - `chrono_start_override`: Optional start date override for chronological ordering.
    - `chrono_end_override`: Optional end date override (must be >= chrono_start_override
      when both are set).
    - `showcase_selected`: Optional boolean to include or exclude from showcase.
    - `compare_attributes`: Optional list of attribute names to enable for comparison.
    - `highlight_skills`: Optional list of skills to highlight for this project.

    Returns:
    - 200: `{"ok": true}` on success.

    Raises:
    - 404 `PROJECT_NOT_FOUND`: No project report exists with the given name.
    - 422: representation_rank is negative, or chrono_end_override is before
      chrono_start_override.
    - 500 `DATABASE_OPERATION_FAILED`: The update failed; changes were rolled back.
    """
    model = get_project_report_model_by_name(session, project_name)
    if not model:
        raise ProjectNotFoundError(f"No project report named {project_name}")

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

        model.last_updated = datetime.now(timezone.utc)
        session.add(model)
        session.commit()
        return {"ok": True}
    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(
            f"Failed to update representation: {str(e)}") from e
