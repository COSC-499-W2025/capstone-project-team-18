from fastapi import APIRouter, Depends
from sqlmodel import SQLModel

from src.interface.api.routers.util import get_session
from src.services.skills_service import get_skills

router = APIRouter(
    prefix="/skills",
    tags=["skills"],
)


class WeightedUserSkills(SQLModel):
    name: str
    weight: float

@router.get("", response_model=dict[str, list[WeightedUserSkills]])
def get_skills_endpoint(session=Depends(get_session)):
    """
    GET /skills

    The skills endpoint will retieve the skills that the user has
    achieved across all their projects. We do this by retieving and
    aggregating all the project skills and then returnting them as
    user skills.

    Returns a list of WeightedUserSkills.
    """
    raw_skills = get_skills(session)

    # Map the dataclass (skill_name) to the response model (name)
    formatted_skills = [WeightedUserSkills(name=s.skill_name, weight=s.weight) for s in raw_skills]

    # Return the mapped data
    return {"skills": formatted_skills}