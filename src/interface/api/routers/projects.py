from fastapi import APIRouter, HTTPException

from src.services.project.retrieve_project_service import(
    retrieve_project_by_id,
    retrieve_projects,
    ProjectResponse,
    AllProjectsResponse
)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.post("/upload")
def upload_project():
    return {"message": "Project uploaded"}


@router.get("", response_model=AllProjectsResponse)
def list_projects():
    """Get all projects from database"""
    return retrieve_projects()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int):
    """Get a single project by ID"""
    project = retrieve_project_by_id(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project
