from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import Session, SQLModel

from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config, UserConfigModel
from src.database.api.CRUD.user_config import UserConfigUpdate
from src.database.api.models import ResumeConfigModel
from src.utils.errors import UserConfigNotFoundError, DatabaseOperationError

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
    skills: Optional[List[str]] = None

class UserConfigRequest(SQLModel):
    """
    Request schema for updating user configuration
    Now includes nested resume_config for education/awards/skills
    """
    consent: bool
    ml_consent: bool = False
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
    skills: List[str] = []


class UserConfigResponse(SQLModel):
    """
    Response schema for user configuration.
    Includes nested resume_config with education/awards/skills
    """
    id: int
    consent: bool
    ml_consent: bool
    user_email: Optional[str] = None
    github: Optional[str] = None
    github_connected: bool = False
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
    :raises UserConfigNotFoundError: if a specific id is given but not found
    :return: The UserConfigModel
    """
    if user_config_id is not None:
        config = session.get(UserConfigModel, user_config_id)
        if not config:
            raise UserConfigNotFoundError(f"No user config found with id {user_config_id}")
        return config

    return get_most_recent_user_config(session)

# ---------- Route Handlers ----------
@router.get("", response_model=UserConfigResponse)
def get_user_config(session=Depends(get_session)):
    """
    Retrieve the current (most recent) user configuration record.

    Returns:
    - 200: A `UserConfigResponse` including any nested resume configuration
      (education, awards, skills)

    Raises:
    - 404 `USER_CONFIG_NOT_FOUND`: No user configuration has been created yet.
    """

    config = get_most_recent_user_config(session)

    if not config:
        raise UserConfigNotFoundError("No user config found")

    # Build response with nested resume config
    resume_config_response = None
    if config.resume_config:
        resume_config_response = ResumeConfigResponse(
            id=config.resume_config.id,
            education=config.resume_config.education or [],
            awards=config.resume_config.awards or [],
            skills=config.resume_config.skills or [],
        )

    return UserConfigResponse(
        id=config.id,
        consent=config.consent,
        ml_consent=config.ml_consent,
        user_email=config.user_email,
        github=config.github,
        github_connected=bool(config.access_token),
        resume_config=resume_config_response,
    )

@router.put("", response_model=UserConfigResponse)
def update_user_config(request: UserConfigRequest, session=Depends(get_session)):
    """
    Create or update the user configuration.

    Persists core fields (consent, email, GitHub) and optionally creates or
    updates the nested ResumeConfigModel (education, awards).

    Body parameters:
    - `consent`: Required boolean consent flag.
    - `user_email`: Required email address.
    - `github`: Optional GitHub username.
    - `resume_config.education`: Optional list of education strings.
    - `resume_config.awards`: Optional list of award strings.
    - `resume_config.skills`: Optional list of skill strings.
    Returns:
    - 200: The updated `UserConfigResponse` with nested resume configuration.

    Raises:
    - 500 `DATABASE_OPERATION_FAILED`: The update failed; changes were rolled back.
    """
    try:
        config = get_most_recent_user_config(session)

        # Build update data for core fields
        update_data = UserConfigUpdate(
            consent=request.consent,
            ml_consent=request.ml_consent,
            user_email=request.user_email,
            github=request.github
        )

        # Update core fields using CRUD function
        config = save_user_config(session, config, update_data)

        # Handle resume config (education/awards/skills)
        if request.resume_config:
            if not config.resume_config:
                # Create new ResumeConfigModel if it doesn't exist
                config.resume_config = ResumeConfigModel(
                    user_config_id=config.id,
                    education=request.resume_config.education or [],
                    awards=request.resume_config.awards or [],
                    skills=request.resume_config.skills or [],
                )
                session.add(config.resume_config)
            else:
                # Update existing ResumeConfigModel
                if request.resume_config.education is not None:
                    config.resume_config.education = request.resume_config.education
                if request.resume_config.awards is not None:
                    config.resume_config.awards = request.resume_config.awards
                if request.resume_config.skills is not None:
                    config.resume_config.skills = request.resume_config.skills
                config.resume_config.last_updated = datetime.now(timezone.utc)

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
                skills=config.resume_config.skills or [],
            )

        return UserConfigResponse(
                id=config.id,
                consent=config.consent,
                ml_consent=config.ml_consent,
                user_email=config.user_email,
                github=config.github,
                github_connected=bool(config.access_token),
                resume_config=resume_config_response,
            )
    except Exception as e:
        session.rollback()
        raise DatabaseOperationError(f"Failed to update user config: {str(e)}") from e
