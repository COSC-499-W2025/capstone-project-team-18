"""
Service for retriving skills
"""

from sqlmodel import Session

from src.database.api.CRUD.projects import get_all_project_ids, get_project_report_by_name
from src.database.core.base import get_engine
from src.core.report import UserReport
from src.core.statistic import WeightedSkills, UserStatCollection
from src.core.report.user.user_statistics import UserWeightedSkills


def get_skills(session: Session) -> list[WeightedSkills]:
    """
    Retrive a user skills. The way we do this is that we get the ids of
    all the projects, and then make a UserReport for that project. Then,
    we can use the user statistic of the skills to return
    """
    project_report_ids = get_all_project_ids(session)

    domain_project_reports = [
        report for pid in project_report_ids
        if (report := get_project_report_by_name(session, pid)) is not None
    ]

    if not domain_project_reports:
        return []

    user_report = UserReport(
        project_reports=domain_project_reports,
        calculator_classes=[UserWeightedSkills],
    )

    skills = user_report.get_value(UserStatCollection.USER_SKILLS.value)
    return skills if skills else []
