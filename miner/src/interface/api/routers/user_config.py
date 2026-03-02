from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlmodel import Session

from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config, UserConfigModel

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
    """
    GET /user-config

    This endpoint retieves the in-use user config. It will respond with
    the config and it's ID.
    """

    user_config = get_most_recent_user_config(session)

    if not user_config:
        raise HTTPException(status_code=404, detail="No user config found")

    return user_config


@router.put("/user-config")
def update_user_config(
    config_update: UserConfigModel,
    session=Depends(get_session)
):
    """
    PUT /user-config

    This endpoint updates the user's config. The values are given in the
    payload, then we save that exact payload to the database and set it
    as the current in use user config (with new id).
    """
    save_user_config(session, config_update)
    session.commit()

    return config_update
