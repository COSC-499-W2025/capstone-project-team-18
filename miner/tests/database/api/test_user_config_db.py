from sqlmodel import Session, select
from src.database.api.CRUD.user_config import get_most_recent_user_config, save_user_config
from src.database.api.models import UserConfigModel
from src.database.api.CRUD.user_config import UserConfigUpdate
from src.database.api.models import ResumeConfigModel


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


def test_resume_config_auto_created_with_user_config(temp_db):
    """Test that ResumeConfigModel is automatically created with UserConfigModel"""
    with Session(temp_db) as session:
        # Clear existing configs
        for instance in session.exec(select(UserConfigModel)).all():
            session.delete(instance)
        session.commit()

        # Create new user config (should auto-create resume config)
        user_config = get_most_recent_user_config(session)

        assert user_config.resume_config is not None
        assert user_config.resume_config.education == []
        assert user_config.resume_config.awards == []


def test_resume_config_persists_with_user_config(temp_db):
    """Test that ResumeConfigModel is saved when UserConfigModel is saved"""
    with Session(temp_db) as session:
        user_config = get_most_recent_user_config(session)

        # Update resume config
        user_config.resume_config.education = ["BSc CS, UBC, 2024"]
        user_config.resume_config.awards = ["Dean's List 2023"]

        session.add(user_config)
        session.commit()
        session.refresh(user_config)

        assert user_config.resume_config.education == ["BSc CS, UBC, 2024"]
        assert user_config.resume_config.awards == ["Dean's List 2023"]


def test_resume_config_one_to_one_relationship(temp_db):
    """Test that only one ResumeConfigModel exists per UserConfigModel"""
    with Session(temp_db) as session:
        user_config = get_most_recent_user_config(session)
        original_resume_config_id = user_config.resume_config.id

        # Try to update (should not create a new resume config)
        user_config.resume_config.education = ["New Education"]
        session.add(user_config)
        session.commit()
        session.refresh(user_config)

        # Should still be the same resume config (same ID)
        assert user_config.resume_config.id == original_resume_config_id
        assert user_config.resume_config.education == ["New Education"]


def test_resume_config_cascade_delete(temp_db):
    """Test that deleting UserConfigModel deletes ResumeConfigModel"""
    with Session(temp_db) as session:
        user_config = get_most_recent_user_config(session)
        resume_config_id = user_config.resume_config.id

        # Delete user config
        session.delete(user_config)
        session.commit()

        # Resume config should also be deleted
        resume_config = session.get(ResumeConfigModel, resume_config_id)
        assert resume_config is None