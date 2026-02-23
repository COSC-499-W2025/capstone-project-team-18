from fastapi import APIRouter

router = APIRouter(
    prefix="/skills",
    tags=["skills"],
)


@router.get("")
def get_skills():
    return {"skills": []}
