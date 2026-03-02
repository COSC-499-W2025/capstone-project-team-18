from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel
from typing import Optional

from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/privacy-consent",
    tags=["privacy-consent"],
)


class PrivacyConsentRequest(SQLModel):
    consent: bool
    user_email: str
    github: Optional[str] = None


class PrivacyConsentResponse(SQLModel):
    message: str
    consent: bool
    user_email: str
    github: Optional[str] = None


@router.post("", response_model=PrivacyConsentResponse)
def set_privacy_consent(
    request: PrivacyConsentRequest,
    session=Depends(get_session)
):
    """
    POST /privacy-consent

    This end point will set the user's privacy config. This endpoint handles
    updates for their consent, user_email, or github.

    This endpoint will respond with the updated fields.
    """

    if not request.user_email:
        raise HTTPException(status_code=400, detail="user_email is required")

    try:
        # get_most_recent_user_config always returns a config (never None)
        config = get_most_recent_user_config(session)

        config.consent = request.consent
        config.user_email = request.user_email
        if request.github is not None:
            config.github = request.github

        update_data = {
            "consent": config.consent,
            "user_email": config.user_email,
            "github": config.github,
            }
        
        save_user_config(session, config, update_data)
        session.commit()

        message = "Consent granted" if request.consent else "Consent revoked"

        return PrivacyConsentResponse(
            message=message,
            consent=config.consent,
            user_email=config.user_email,
            github=config.github,
        )

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save consent: {str(e)}"
        )
