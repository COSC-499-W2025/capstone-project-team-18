from fastapi import APIRouter, Depends, HTTPException
from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config, UserConfigModel

router = APIRouter(
    prefix="",
    tags=["user-config"],
)


@router.get("/user-config")
def get_user_config(session=Depends(get_session)) -> UserConfigModel:

    user_config = get_most_recent_user_config(session)

    if not user_config:
        raise HTTPException(status_code=404, detail="No user config found")

    return user_config


@router.put("/user-config")
def update_user_config(
    config_update: UserConfigModel,
    session=Depends(get_session)
):
    save_user_config(session, config_update)
    return config_update
