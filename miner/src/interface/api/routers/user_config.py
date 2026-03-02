from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlmodel import Session

from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config, UserConfigModel
from src.database.api.CRUD.user_config import UserConfigUpdate

router = APIRouter(
    prefix="",
    tags=["user-config"],
)


def get_user_config_safe(
    session: Session,
    user_config_id: Optional[int] = None
) -> UserConfigModel:
    """
    Get user config by id, error if no config found. If id not
    provided, get the most recent user config.

    :param session: The database session
    :param user_config_id: Optional ID of the user config to retrieve
    :raises HTTPException: 404 if a specific id is given but not found
    :return: The UserConfigModel
    """
    if user_config_id is not None:
        config = session.get(UserConfigModel, user_config_id)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"No user config found with id {user_config_id}"
            )
        return config

    return get_most_recent_user_config(session)


@router.get("/user-config")
def get_user_config(session=Depends(get_session)) -> UserConfigModel:

    user_config = get_most_recent_user_config(session)

    if not user_config:
        raise HTTPException(status_code=404, detail="No user config found")

    return user_config


@router.put("/user-config/{config_id}")
def update_user_config(
    config_id: int,
    config_update: UserConfigUpdate,
    session=Depends(get_session)
):
    # Fetch the existing record
    db_config = session.get(UserConfigModel, config_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Config not found")

    # Update and save
    updated_config = save_user_config(session, db_config, config_update)
    session.commit()
    session.refresh(updated_config)

    return updated_config
