"""
Database CRUD for the resume object
"""

from sqlmodel import Session
from src.core.resume.resume import Resume
from src.database.api.models import ResumeModel
from src.database.core.model_seralizer import (
    serialize_resume,
    serialize_resume_item,
)


def save_resume(
    session: Session,
    resume: Resume
) -> ResumeModel:
    """
    Save a Resume domain object into the DB.
    """

    resume_model = serialize_resume(resume)

    resume_item_models = [serialize_resume_item(ri) for ri in resume.items]

    resume_model.items = resume_item_models

    session.add(resume_model)
    session.commit()
    session.refresh(resume_model)

    return resume_model
