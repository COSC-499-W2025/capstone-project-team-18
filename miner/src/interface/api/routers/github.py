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

from src.infrastructure.log.logging import get_logger
from src.database.api.CRUD.github import get_access_token, revoke_access_token
from src.interface.api.routers.util import get_session
from src.database import get_most_recent_user_config

logger = get_logger(__name__)

router = APIRouter(
    prefix="/github",
    tags=["github"],
)

OAUTH_STATE_TTL_SECONDS = 600
_oauth_states: dict[str, dict[str, str | float | None]] = {}
DEFAULT_ELECTRON_CALLBACK_SCHEME = "capstone"


def _app_callback_base_url() -> str:
    """Builds the app deep-link base URL, e.g. capstone://oauth-callback."""
    scheme = os.environ.get("ELECTRON_CALLBACK_SCHEME",
                            DEFAULT_ELECTRON_CALLBACK_SCHEME)
    return f"{scheme}://oauth-callback"


def _build_app_deep_link(state: str, status: str, detail: str | None = None) -> str:
    params = {
        "state": state,
        "status": status,
    }
    if detail:
        params["detail"] = detail
    return f"{_app_callback_base_url()}?{urlencode(params)}"


def _oauth_complete_page(target_url: str) -> HTMLResponse:
    html = f"""
        <!doctype html>
        <html>
            <head>
                <meta charset=\"utf-8\" />
                <title>GitHub Authentication Complete</title>
            </head>
            <body>
                <p>Returning to the app...</p>
                <script>
                    window.location.href = {target_url!r};
                    setTimeout(function () {{
                        window.location.replace({target_url!r});
                    }}, 200);
                </script>
            </body>
        </html>
    """
    return HTMLResponse(content=html)


def _new_oauth_state() -> str:
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
    '''
    oauth_state = _oauth_states.get(state)
    if not oauth_state:
        raise HTTPException(status_code=404, detail="Unknown OAuth state")

    created_at = oauth_state.get("created_at")
    if isinstance(created_at, float) and time.time() - created_at > OAUTH_STATE_TTL_SECONDS:
        del _oauth_states[state]
        raise HTTPException(status_code=410, detail="OAuth state expired")

    return oauth_state


@router.get("/login")
def github_login():
    """
    `GET /github/login`

    Called by the frontend to generate an OAuth state. Generates and returns a
    GitHub authorization URL. The frontend should open the URL with the OS browser.
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
        "callback_scheme": os.environ.get("ELECTRON_CALLBACK_SCHEME", DEFAULT_ELECTRON_CALLBACK_SCHEME),
    }


@router.get("/oauth-status")
def github_oauth_status(state: str):
    """
    `GET /github/oauth-status?state=...`

    Returns the backend OAuth status for a generated state.
    """
    oauth_state = _get_oauth_state_or_raise(state)
    return {
        "state": state,
        "status": oauth_state.get("status"),
        "detail": oauth_state.get("detail"),
    }


'''
1. On the frontend, Electron needs to open the user's browser and send them to
https://github.com/login/oauth/authorize?client_id=YOUR_CLIENT_ID&scope=repo

2.  The user clicks "accept" and a request is made to the callback URL (our endpoint)

3. At the /github/callback endpoint, the backend exchanges the auth code for an access
token by making a server-side POST request (with client secret) to GitHub. We can then use this token to
do things on the user's behalf, such as uploading files to a repo.
'''


@router.get("/callback")
async def github_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
    session=Depends(get_session)
):
    '''
    `GET /callback`

    e.g., http://localhost:8000/api/github/callback?code=abcdef123456
    '''

    oauth_state = _get_oauth_state_or_raise(state)

    if error:
        status = "denied" if error == "access_denied" else "error"
        oauth_state["status"] = status
        oauth_state["detail"] = error
        return _oauth_complete_page(_build_app_deep_link(state, status, error))

    if not code:
        oauth_state["status"] = "error"
        oauth_state["detail"] = "GitHub auth code missing"
        return _oauth_complete_page(
            _build_app_deep_link(state, "error", "GitHub auth code missing")
        )

    db_config = get_most_recent_user_config(session)
    if not db_config:
        oauth_state["status"] = "error"
        oauth_state["detail"] = "Config not found"
        return _oauth_complete_page(_build_app_deep_link(state, "error", "Config not found"))

    try:
        await get_access_token(session, db_config, code)
        session.commit()
        session.refresh(db_config)
        oauth_state["status"] = "success"
        oauth_state["detail"] = None
        return _oauth_complete_page(_build_app_deep_link(state, "success"))
    except HTTPException as exc:
        session.rollback()
        oauth_state["status"] = "error"
        oauth_state["detail"] = str(exc.detail)
        return _oauth_complete_page(_build_app_deep_link(state, "error", str(exc.detail)))


@router.put("/revoke_access_token")
def revoke_token(session=Depends(get_session)):
    '''
    `PUT /revoke_acces_token`

    This endpoint sets the `access_token` col in the `UserConfigModel` to `None`.

    - **NOTE:** This endpoint should be called in conjunction with frontend logic
    send the user to https://github.com/settings/applications so that they can revoke
    access on their end too.
    '''
    db_config = get_most_recent_user_config(session)
    if not db_config:
        raise HTTPException(status_code=404, detail="Config not found")

    updated_config = revoke_access_token(session, db_config)

    if updated_config.access_token is not None:
        raise HTTPException(
            status_code=400, detail="Error revoking access token")

    session.commit()
    session.refresh(updated_config)
    return {"message": "Access token revoked"}
