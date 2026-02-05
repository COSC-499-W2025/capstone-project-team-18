
from sqlmodel import Session, select
from src.database.api.models import UserConfigModel


def get_most_recent_user_config(session: Session) -> UserConfigModel | None:
    """
    Retrieve the most recent UserConfigModel based on max(id)
    """

    statement = select(UserConfigModel).order_by(
        UserConfigModel.id).limit(1)  # pyright: ignore[reportArgumentType]

    return session.exec(statement).first()


def save_user_config(session: Session, user_config: UserConfigModel) -> UserConfigModel | None:
    """
    Write the passed UserConfigModel to the database. This config will
    then become the defacto configuration
    """

    session.add(user_config)
    session.commit()
    session.refresh(user_config)

    return user_config
