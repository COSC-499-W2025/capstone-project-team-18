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
    Aggregate and return all skills detected across every project report.

    Skills are weighted by their relative contribution across projects, then
    returned as a flat list sorted by the service layer.

    Returns:
    - 200: `{"skills": [{"name": "...", "weight": 0.0}]}` — a list of
      `WeightedUserSkills` sorted by the service layer.
    """
    raw_skills = get_skills(session)

    # Map the dataclass (skill_name) to the response model (name)
    formatted_skills = [WeightedUserSkills(name=s.skill_name, weight=s.weight) for s in raw_skills]

    # Return the mapped data
    return {"skills": formatted_skills}

@router.get("/highlighted", response_model=dict[str, list[WeightedUserSkills]])
def get_highlighted_skills(session=Depends(get_session)):
    """
    Return only the skills that have been manually highlighted on at least one project.

    A skill is highlighted when it appears in a project's `highlight_skills` list,
    set via PATCH /projects/{project_name}/representation.

    Returns:
    - 200: `{"skills": [{"name": "...", "weight": 0.0}]}` — subset of all skills,
      sorted alphabetically. Weight is 0.0 if the skill has not been detected by
      the analyzer.
    """
    from src.database.api.CRUD.projects import get_all_project_report_models

    projects = get_all_project_report_models(session)
    highlighted = set()
    for p in projects:
        for s in (p.highlight_skills or []):
            highlighted.add(s)

    raw = get_skills(session)
    weights = {s.skill_name: s.weight for s in raw}

    return {
        "skills": [WeightedUserSkills(name=k, weight=weights.get(k, 0.0)) for k in sorted(highlighted)]
    }