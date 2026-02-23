from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel

from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config, save_user_config, UserConfigModel

router = APIRouter(
    prefix="/privacy-consent",
    tags=["privacy-consent"],
)


class PrivacyConsentRequest(SQLModel):
    consent: bool
    user_email: str


class PrivacyConsentResponse(SQLModel):
    message: str
    consent: bool
    user_email: str


@router.post("", response_model=PrivacyConsentResponse)
def set_privacy_consent(
    request: PrivacyConsentRequest,
    session=Depends(get_session)
):
    """Set the user's privacy consent."""
    if not request.user_email:
        raise HTTPException(status_code=400, detail="user_email is required")

    try:
        config = get_most_recent_user_config(session)

        if config is None:
            config = UserConfigModel(
                user_email=request.user_email,
                consent=request.consent
            )
        else:
            config.consent = request.consent
            config.user_email = request.user_email

        save_user_config(session, config)
        session.commit()

        message = "Consent granted" if request.consent else "Consent revoked"

        return PrivacyConsentResponse(
            message=message,
            consent=request.consent,
            user_email=request.user_email
        )

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save consent: {str(e)}"
        )