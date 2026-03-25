"""
Database CRUD for the resume object
"""

from typing import Optional
from src.database.core.model_deserializer import deserialize_resume
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from src.core.resume.resume import Resume
from src.database.api.models import ResumeModel
from src.database.core.model_serializer import (
    serialize_resume,
    serialize_resume_item,
)


def save_resume(
    session: Session,
    resume: Resume
) -> ResumeModel:
    """
    Save a Resume domain object into the DB. DOES NOT COMMIT THE
    SESSION! YOU MUST COMMIT.
    """

    resume_model = serialize_resume(resume)

    resume_item_models = [serialize_resume_item(ri) for ri in resume.items]

    resume_model.items = resume_item_models

    session.add(resume_model)

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

def get_resume_model_by_id(session: Session, resume_id: int) -> Optional[ResumeModel]:
    """
    Get the ResumeModel directly ie not deserialized to domain object
    """
    statement = (
        select(ResumeModel)
        .where(ResumeModel.id == resume_id)
        .options(selectinload(ResumeModel.items))  # pyright: ignore
    )
    return session.exec(statement).first()

def list_resumes(session: Session) -> list[ResumeModel]:
    """
    Returns a lightweight list of all produced resumes.
    Loads resume items so item_count can be derived by the router.
    Most recently updated resumes are returned first.
    """
    statement = (
        select(ResumeModel)
        .options(selectinload(ResumeModel.items))  # pyright: ignore
        .order_by(ResumeModel.last_updated.desc())
    )
    return list(session.exec(statement).all())