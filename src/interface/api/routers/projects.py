from fastapi import APIRouter

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.post("/upload")
def upload_project():
    return {"message": "Project uploaded"}


@router.get("")
def list_projects():
    return {"projects": []}


@router.get("/{project_id}")
def get_project(project_id: str):
    return {"project_id": project_id}
