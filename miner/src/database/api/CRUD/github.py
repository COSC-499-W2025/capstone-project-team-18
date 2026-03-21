'''
Make a POST req to GitHub for the user's
access token after they give perms.
'''
import os
import httpx  # for making the external request to GitHub
from fastapi import HTTPException
from sqlmodel import Session

from src.database.api.models import UserConfigModel


async def get_access_token(
        session: Session,
        db_config: UserConfigModel,
        code: str
):
    '''
    Handles the redirect from GitHub after the user has given
    permission to access their repos via the REST API.

    GitHub passes the authorization 'code' as a query parameter.
    '''
    # GitHub's endpoint that we send the user to
    token_url = "https://github.com/login/oauth/access_token"

    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth is not configured on the server"
        )

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data=payload,
            headers={"Accept": "application/json"}
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="GitHub token exchange failed"
        )

    data = response.json()

    if "error" in data:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub Error: {data.get('error_description', 'Unknown error')}"
        )

    acc_toke = data.get("access_token")
    if not acc_toke:
        raise HTTPException(
            status_code=502,
            detail="GitHub response is missing access token"
        )

    setattr(db_config, "access_token", acc_toke)
    session.add(db_config)
    return acc_toke


def revoke_access_token(
    session: Session,
    db_config: UserConfigModel,
):
    setattr(db_config, "access_token", None)  # set access token to NULL
    session.add(db_config)
    return db_config
