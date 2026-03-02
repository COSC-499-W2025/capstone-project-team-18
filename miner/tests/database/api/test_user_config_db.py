from sqlmodel import Session, select
from src.database.api.CRUD.user_config import get_most_recent_user_config, save_user_config
from src.database.api.models import UserConfigModel
from src.database.api.CRUD.user_config import UserConfigUpdate


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
    update_data = UserConfigUpdate(
        user_email="sam@gmail.com", github="sam-github")

    with Session(temp_db) as session:
        db_config = get_most_recent_user_config(session)

        updated_uc = save_user_config(session, db_config, update_data)
        session.commit()

        session.refresh(updated_uc)
        assert updated_uc.user_email == "sam@gmail.com"
        assert updated_uc.github == "sam-github"


def test_many_different_user_config_object(temp_db):
    update1 = UserConfigUpdate(user_email="sam@gmail.com", github="sam-github")
    update2 = UserConfigUpdate(
        user_email="spencer@gmail.com", github="spencer-github")

    with Session(temp_db) as session:
        db_config = get_most_recent_user_config(session)
        save_user_config(session, db_config, update1)
        session.commit()

        db_config = get_most_recent_user_config(session)
        save_user_config(session, db_config, update2)
        session.commit()

        latest = get_most_recent_user_config(session)
        assert latest.user_email == "spencer@gmail.com"
        assert latest.github == "spencer-github"
