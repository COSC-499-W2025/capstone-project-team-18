from sqlmodel import Session, select
from src.database.api.CRUD.user_config import get_most_recent_user_config, save_user_config
from src.database.api.models import UserConfigModel


def test_user_config_auto_created(temp_db):

    statement = select(UserConfigModel)

    with Session(temp_db) as session:
        results = session.exec(statement).all()

        for instance in results:
            session.delete(instance)
        session.commit()

        # Should create a new one automatically
        user_config = get_most_recent_user_config(session)
        assert user_config is not None
        assert user_config.id is not None
        assert user_config.user_email is None
        assert user_config.github is None


def test_saving_user_config_object(temp_db):

    uc = UserConfigModel()
    uc.user_email = "sam@gmail.com"
    uc.github = "sam-github"

    with Session(temp_db) as session:
        updated_uc = save_user_config(session, uc)
        user_config = get_most_recent_user_config(session)

        assert updated_uc is not None
        assert user_config is not None
        assert updated_uc.id == user_config.id
        assert user_config.user_email == "sam@gmail.com"
        assert user_config.github == "sam-github"


def test_many_different_user_config_object(temp_db):

    uc1 = UserConfigModel()
    uc1.user_email = "sam@gmail.com"
    uc1.github = "sam-github"

    uc2 = UserConfigModel()
    uc2.user_email = "spencer@gmail.com"
    uc2.github = "spencer-github"

    with Session(temp_db) as session:
        updated_uc1 = save_user_config(session, uc1)
        updated_uc2 = save_user_config(session, uc2)

        user_config = get_most_recent_user_config(session)

        assert updated_uc1 is not None
        assert updated_uc2 is not None
        assert user_config is not None
        assert updated_uc1 != updated_uc2
        assert updated_uc2.id == user_config.id
        assert user_config.user_email == "spencer@gmail.com"
        assert user_config.github == "spencer-github"
