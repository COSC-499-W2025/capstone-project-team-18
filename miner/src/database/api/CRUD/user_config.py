
from sqlmodel import Session, select, desc
from src.database.api.models import UserConfigModel


def get_most_recent_user_config(session: Session) -> UserConfigModel:
    """
    Retrieve the most recent UserConfigModel based on max(id). If a user
    has not set a user_config variable, this will automatically a deafult
    UserConfig and store it in the database.
    """

    statement = select(UserConfigModel).order_by(
        desc(UserConfigModel.id)).limit(1)

    user_config = session.exec(statement).first()

    if user_config is None:
        # If a user hasn't made a user_config, make a user_config
        # with None values and store it in the database
        user_config = UserConfigModel(
            id=None,
            user_email=None,
            github=None
        )
        session.add(user_config)
        session.commit()
        session.refresh(user_config)

    return user_config


def save_user_config(session: Session, user_config: UserConfigModel) -> UserConfigModel | None:
    """
    Write the passed UserConfigModel to the database. This config will
    then become the defacto configuration. DOES NOT COMMIT THE
    SESSION! YOU MUST COMMIT.
    """

    session.add(user_config)

    return user_config
