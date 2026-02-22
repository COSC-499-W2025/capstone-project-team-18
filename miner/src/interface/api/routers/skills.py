from fastapi import APIRouter
from sqlmodel import SQLModel

from src.services.skills_service import get_skills

router = APIRouter(
    prefix="/skills",
    tags=["skills"],
)


class WeightedUserSkills(SQLModel):
    name: str
    weight: float


@router.get("", response_model=dict[str, list[WeightedUserSkills]])
def get_skills_endpoint():
    """
    Retrieve user skills and format them for the API response.
    """
    # 1. Fetch raw skills from the service layer
    raw_skills = get_skills()

    # 2. Map the dataclass (skill_name) to the response model (name)
    formatted_skills = [
        WeightedUserSkills(name=skill.skill_name, weight=skill.weight)
        for skill in raw_skills
    ]

    # 3. Return the mapped data
    return {"skills": formatted_skills}
