from fastapi import APIRouter

router = APIRouter(
    prefix="/resume",
    tags=["resume"],
)


@router.get("/{resume_id}")
def get_resume(resume_id: str):
    return {"resume_id": resume_id}


@router.post("/generate")
def generate_resume():
    return {"status": "resume generated"}


@router.post("/{resume_id}/edit")
def edit_resume(resume_id: str):
    return {"resume_id": resume_id, "status": "edited"}
