"""
Contains endpoints related to gaining access to the user's
GitHub account and uploading a GitHub Pages site for them.
"""
import os
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from src.database.api.CRUD.github import get_access_token, revoke_access_token
from src.database import get_most_recent_user_config
from src.infrastructure.log.logging import get_logger
from src.interface.api.routers.util import get_session
from src.utils.errors import UserConfigNotFoundError, DatabaseOperationError, BadOAuthStateError, ExpiredOAuthState

logger = get_logger(__name__)

router = APIRouter(
    prefix="/github",
    tags=["github"],
)

OAUTH_STATE_TTL_SECONDS = 600  # OAuth state expires after 600 sec
_oauth_states: dict[str, dict[str, str | float | None]] = {}


def _oauth_complete_page(status: str, detail: str | None = None) -> HTMLResponse:
    '''
    Helper function for the `/callback` endpoint. This generates
    a small piece of HTML to show in the browser after GitHub OAuth
    finishes. The Electron app is notified via the polling fallback
    at `/github/oauth-status`.
    '''
    message = "You can close this tab and return to the app."

    if status == "success":
        heading = "GitHub connected successfully!"
        message = message
    elif status == "denied":
        heading = "GitHub access denied."
        message = f"You declined to grant access. {message}"
    else:
        heading = "Something went wrong."
        message = detail or f"An unexpected error occurred. {message}"

    html = f"""
        <!doctype html>
        <html>
            <head>
                <meta charset="utf-8" />
                <title>GitHub Authentication</title>
            </head>
            <body>
                <h2>{heading}</h2>
                <p>{message}</p>
            </body>
        </html>
    """

    return HTMLResponse(content=html)


def _new_oauth_state() -> str:
    '''Generates a new OAuth state'''
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "status": "pending",
        "detail": None,
        "created_at": time.time(),
    }
    return state


def _get_oauth_state_or_raise(state: str) -> dict[str, str | float | None]:
    '''
    Validates the OAuth state that is passed in a request to `/github/callback`

    Returns:
    - 200: The valid (known and not expired) OAuth state

    Raises:
    - 404 `BAD_OAUTH_STATE`: OAuth state is unknown
    - 410 `EXPIRED_OAUTH_STATE`: OAuth state has expired.
    '''
    oauth_state = _oauth_states.get(state)
    if not oauth_state:
        raise BadOAuthStateError("Unknown OAuth State")

    created_at = oauth_state.get("created_at")
    if isinstance(created_at, float) and time.time() - created_at > OAUTH_STATE_TTL_SECONDS:
        del _oauth_states[state]
        raise ExpiredOAuthState("OAuth State Expired")

    return oauth_state


@router.get("/login")
def github_login():
    """
    Called by the frontend to generate an OAuth state. Generates and returns a
    GitHub authorization URL. The frontend should open the URL with the OS browser
    to get the user's auth code (which will be used to get the access token).

    Returns:
    - 200: JSON object that contains the OAuth state, the auth URL, and the callback scheme.

    Raises:
    - 500: GITHUB_CLIENT_ID and/or GITHUB_REDIRECT_URI missing from `.env`.
    """
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    redirect_uri = os.environ.get("GITHUB_REDIRECT_URI")

    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID and GITHUB_REDIRECT_URI must be set"
        )

    state = _new_oauth_state()
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "repo",
        "state": state,
    })
    authorization_url = f"https://github.com/login/oauth/authorize?{query}"

    return {
        "state": state,
        "authorization_url": authorization_url,
        "callback_scheme": "capstone",
    }


@router.get("/oauth-status")
def github_oauth_status(state: str):
    """
    Called by the frontend every 2 sec to poll the
    backend OAuth status for a generated state.

    This is a fallback if the deep link fails so
    that the frontend still knowns what the result
    (user accepts or denies) is so that it can switch
    from "pending" to "Connected".
    """
    oauth_state = _get_oauth_state_or_raise(state)
    return {
        "state": state,
        "status": oauth_state.get("status"),
        "detail": oauth_state.get("detail"),
    }


@router.get("/callback")
async def github_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
    session=Depends(get_session)
):
    '''
    Called by GitHub when the user does (or doesn't) authenticate our app.

    This gives us the auth code, which we use to get the access token
    (needed to take action on the user's behalf). A short piece of HTML
    to prompt the user to reopen our Electron app is returned in response.
    - e.g., http://localhost:8000/api/github/callback?code=abcdef123456

    Body Parameters:
    - `state`: The OAuth State
    - `code`: The authorization code that is generated after the user
    gives permission for our app to take action on their behalf.
    - `error`: Passed in if an error occurs, such as the user denying access.

    Returns:
    - 200: An HTML popup in the browswer prompting the user to return to the
    Electron app.

    Raises:
    - Error: Thrown when the user denies access or another error occurs
    - Code Error: Missing authorization code
    - No user configuration has been created yet (equivalent to `USER_CONFIG_NOT_FOUND`).
    - HTTP Error: Error generating HTML page for popup to return to Electron.
    '''

    oauth_state = _get_oauth_state_or_raise(state)

    # Validate the callback request
    if error:
        status = "denied" if error == "access_denied" else "error"
        oauth_state["status"] = status
        oauth_state["detail"] = error
        return _oauth_complete_page(status, error)

    if not code:
        oauth_state["status"] = "error"
        oauth_state["detail"] = "GitHub auth code missing"
        return _oauth_complete_page("error", "GitHub auth code missing")

    db_config = get_most_recent_user_config(session)
    if not db_config:
        oauth_state["status"] = "error"
        oauth_state["detail"] = "Config not found"
        return _oauth_complete_page("error", "Config not found")

    # Get and store the access token in the DB.
    try:
        await get_access_token(session, db_config, code)
        session.commit()
        session.refresh(db_config)
        oauth_state["status"] = "success"
        oauth_state["detail"] = None
        return _oauth_complete_page("success")
    except HTTPException as exc:
        session.rollback()
        oauth_state["status"] = "error"
        oauth_state["detail"] = str(exc.detail)
        return _oauth_complete_page("error", str(exc.detail))


@router.put("/revoke_access_token")
def revoke_token(session=Depends(get_session)):
    '''
    Sets the `access_token` col in the `UserConfigModel` to `None`.

    Returns:
    - 200: Success message that the access token was revoked.

    Raises:
    - 404 `USER_CONFIG_NOT_FOUND`: No user configuration has been created yet.
    - 500 `DATABASE_OPERATION_FAILED`: Failed to set user's access token to `None`

    - **NOTE:** This endpoint should be called in conjunction with frontend logic
    to send the user to https://github.com/settings/applications so that they can
    revoke access on their end too.
    '''
    db_config = get_most_recent_user_config(session)
    if not db_config:
        raise UserConfigNotFoundError("No user config found")

    updated_config = revoke_access_token(session, db_config)

    if updated_config.access_token is not None:
        raise DatabaseOperationError("Error revoking access token")

    session.commit()
    session.refresh(updated_config)
    return {"message": "Access token revoked"}
