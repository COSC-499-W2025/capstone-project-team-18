from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from sqlmodel import Session, SQLModel

from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config, UserConfigModel
from src.database.api.CRUD.user_config import UserConfigUpdate

router = APIRouter(
    prefix="/user-config",
    tags=["user-config"],
)

# ---------- Request/Response Models ----------
class UserConfigRequest(SQLModel):
    """
    Request schema for updating user configuration.
    """
    consent: bool
    user_email: str
    github: Optional[str] = None
    education: Optional[List[str]] = None
    awards: Optional[List[str]] = None

class UserConfigResponse(SQLModel):
    """
    Response schema for user configuration.
    """
    id: int
    consent: bool
    user_email: str
    github: Optional[str] = None
    education: Optional[List[str]] = None
    awards: Optional[List[str]] = None



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


# @router.get("/user-config")
# def get_user_config(session=Depends(get_session)) -> UserConfigModel:
#     """
#     GET /user-config

#     This endpoint retieves the in-use user config. It will respond with
#     the config and it's ID.
#     """

#     user_config = get_most_recent_user_config(session)

#     if not user_config:
#         raise HTTPException(status_code=404, detail="No user config found")

#     return user_config


# @router.put("/user-config/{config_id}")
# def update_user_config(
#     config_id: int,
#     config_update: UserConfigUpdate,
#     session=Depends(get_session)
# ):
#     """
#     PUT /user-config

#     This endpoint updates the user's config. The values are given in the
#     payload, then we save that exact payload to the database and set it
#     as the current in use user config (with new id).
#     """
#     # Fetch the existing record
#     db_config = session.get(UserConfigModel, config_id)
#     if not db_config:
#         raise HTTPException(status_code=404, detail="Config not found")

#     # Update and save
#     updated_config = save_user_config(session, db_config, config_update)
#     session.commit()
#     session.refresh(updated_config)

#     return updated_config



@router.get("", response_model=UserConfigResponse)
def get_user_config(session=Depends(get_session)):
    """
    Retrieve the current user configuration.
    Returns 404 if no config exists
    """
    config = get_most_recent_user_config(session)
    if not config:
        raise HTTPException(status_code=404, detail="User config not found")

    return UserConfigResponse(
        id=config.id,
        consent=config.consent,
        user_email=config.user_email,
        github=config.github,
        # Normalize None to empty list
        education=config.education or [],
        awards=config.awards or [],
    )


@router.put("", response_model=UserConfigResponse)
def put_user_config(request: UserConfigRequest, session=Depends(get_session)):
    """
    Update user configuration with new settings.
    """
    try:
        config = get_most_recent_user_config(session)

        # Update core fields
        config.consent = request.consent
        config.user_email = request.user_email
        config.github = request.github

        # Update education and awards only if client explicitly sends them
        # ie this allows users to update awards and education independently of eachoter
        if request.education is not None:
            config.education = request.education
        if request.awards is not None:
            config.awards = request.awards

        # Persist changes to database
        save_user_config(session, config)
        session.commit()

        return UserConfigResponse(
            id=config.id,
            consent=config.consent,
            user_email=config.user_email,
            github=config.github,
            education=config.education or [],
            awards=config.awards or [],
        )
    except Exception as e:
        # Roll back transaction if save fails
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))