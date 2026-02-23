from sqlmodel import Session
from src.database.core.base import get_engine


def get_session():
    engine = get_engine()
    with Session(engine) as session:
        yield session
