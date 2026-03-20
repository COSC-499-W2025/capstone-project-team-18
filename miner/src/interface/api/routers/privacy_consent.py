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
    Set or update the user's privacy consent and contact details.

    Persists consent, email, and optional GitHub username to the most recent
    user config record.

    Body parameters:
    - `consent`: Required boolean consent flag.
    - `user_email`: Required email address (must be non-empty).
    - `github`: Optional GitHub username.

    Returns:
    - 200: A `PrivacyConsentResponse` with message, consent, user_email, and github.

    Raises:
    - 400: user_email is not provided in the request body.
    - 500: The consent record could not be saved; changes were rolled back.
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

        save_user_config(session, config, request)
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
