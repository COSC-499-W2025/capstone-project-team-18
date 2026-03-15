from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, SQLModel

from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config, UserConfigModel
from src.database.api.CRUD.user_config import UserConfigUpdate
from src.database.api.models import ResumeConfigModel

router = APIRouter(
    prefix="/user-config",
    tags=["user-config"],
)

# ---------- Request/Response Schemas ----------
class ResumeConfigRequest(SQLModel):
    """
    Nested request model for resume configuration.
    """
    education: Optional[List[str]] = None
    awards: Optional[List[str]] = None


class UserConfigRequest(SQLModel):
    """
    Request schema for updating user configuration.
    Now includes nested resume_config for education/awards.
    """
    consent: bool
    user_email: str
    github: Optional[str] = None
    resume_config: Optional[ResumeConfigRequest] = None


class ResumeConfigResponse(SQLModel):
    """
    Nested response model for resume configuration.
    """
    id: int
    education: List[str] = []
    awards: List[str] = []


class UserConfigResponse(SQLModel):
    """
    Response schema for user configuration.
    Includes nested resume_config with education/awards.
    """
    id: int
    consent: bool
    user_email: Optional[str] = None
    github: Optional[str] = None
    resume_config: Optional[ResumeConfigResponse] = None


# ---------- Helper Functions ----------
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

# ---------- Route Handlers ----------
@router.get("", response_model=UserConfigResponse)
def get_user_config(session=Depends(get_session)):
    """
    GET /user-config

    This endpoint retieves the in-use user config. It will respond with
    the config and it's ID.
    """

    config = get_most_recent_user_config(session)

    if not config:
        raise HTTPException(status_code=404, detail="No user config found")

    # Build response with nested resume config
    resume_config_response = None
    if config.resume_config:
        resume_config_response = ResumeConfigResponse(
            id=config.resume_config.id,
            education=config.resume_config.education or [],
            awards=config.resume_config.awards or [],
        )

    return UserConfigResponse(
        id=config.id,
        consent=config.consent,
        user_email=config.user_email,
        github=config.github,
        resume_config=resume_config_response,
    )

@router.put("", response_model=UserConfigResponse)
def update_user_config(request: UserConfigRequest, session=Depends(get_session)):
    """
    PUT /user-config

    This endpoint updates the user's config. The values are given in the
    payload, then we save that exact payload to the database and set it
    as the current in use user config (with new id).

    Creates ResumeConfigModel if it doesn't exist, or updates existing one.
    """
    try:
        config = get_most_recent_user_config(session)

        # Build update data for core fields
        update_data = UserConfigUpdate(
            consent=request.consent,
            user_email=request.user_email,
            github=request.github
        )

        # Update core fields using CRUD function
        config = save_user_config(session, config, update_data)

        # Handle resume config (education/awards)
        if request.resume_config:
            if not config.resume_config:
                # Create new ResumeConfigModel if it doesn't exist
                config.resume_config = ResumeConfigModel(
                    user_config_id=config.id,
                    education=request.resume_config.education or [],
                    awards=request.resume_config.awards or [],
                )
                session.add(config.resume_config)
            else:
                # Update existing ResumeConfigModel
                if request.resume_config.education is not None:
                    config.resume_config.education = request.resume_config.education
                if request.resume_config.awards is not None:
                    config.resume_config.awards = request.resume_config.awards
                config.resume_config.last_updated = datetime.now()

        # Persist changes

        session.commit()
        session.refresh(config)

        # Build response
        resume_config_response = None
        if config.resume_config:
            resume_config_response = ResumeConfigResponse(
                id=config.resume_config.id,
                education=config.resume_config.education or [],
                awards=config.resume_config.awards or [],
            )

        return UserConfigResponse(
                id=config.id,
                consent=config.consent,
                user_email=config.user_email,
                github=config.github,
                resume_config=resume_config_response,
            )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
