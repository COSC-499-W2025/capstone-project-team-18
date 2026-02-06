"""
Database CRUD for the resume object
"""

from typing import Optional
from src.database.core.model_deseralizer import deserialize_resume
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
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


def load_resume(session: Session, resume_id: int) -> Optional[Resume]:
    """
    Load a Resume from the database by ID and convert it
    into the domain Resume object.
    """

    statement = (
        select(ResumeModel)
        .where(ResumeModel.id == resume_id)
        .options(selectinload(ResumeModel.items))  # pyright: ignore
    )

    model = session.exec(statement).first()

    if model is None:
        return None

    return deserialize_resume(model)
