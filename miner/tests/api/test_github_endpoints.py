"""
Tests for GitHub OAuth endpoints:
  GET  /github/login
  GET  /github/oauth-status
  GET  /github/callback
  PUT  /github/revoke_access_token
"""
import os
from unittest.mock import patch, MagicMock

import src.interface.api.routers.github as github_mod


# ---------------------------------------------------------------------------
# GET /github/login
# ---------------------------------------------------------------------------

class TestGithubLogin:
    def test_returns_state_and_url_when_env_set(self, client):
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test-client-id",
            "GITHUB_REDIRECT_URI": "http://localhost/callback",
        }):
            r = client.get("/github/login")
        assert r.status_code == 200
        body = r.json()
        assert "state" in body
        assert "authorization_url" in body
        assert "test-client-id" in body["authorization_url"]

    def test_returns_500_when_client_id_missing(self, client):
        env = {"GITHUB_REDIRECT_URI": "http://localhost/callback"}
        env.pop("GITHUB_CLIENT_ID", None)
        with patch.dict(os.environ, env, clear=False):
            # Ensure GITHUB_CLIENT_ID is absent
            os.environ.pop("GITHUB_CLIENT_ID", None)
            r = client.get("/github/login")
        assert r.status_code == 500

    def test_returns_500_when_redirect_uri_missing(self, client):
        os.environ.pop("GITHUB_REDIRECT_URI", None)
        with patch.dict(os.environ, {"GITHUB_CLIENT_ID": "id"}, clear=False):
            os.environ.pop("GITHUB_REDIRECT_URI", None)
            r = client.get("/github/login")
        assert r.status_code == 500

    def test_state_is_registered(self, client):
        """After login, the returned state should be pollable."""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "cid",
            "GITHUB_REDIRECT_URI": "http://localhost/cb",
        }):
            login_r = client.get("/github/login")
        state = login_r.json()["state"]

        r = client.get(f"/github/oauth-status?state={state}")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_authorization_url_contains_scope_repo(self, client):
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "cid",
            "GITHUB_REDIRECT_URI": "http://localhost/cb",
        }):
            r = client.get("/github/login")
        assert "scope=repo" in r.json()["authorization_url"]


# ---------------------------------------------------------------------------
# GET /github/oauth-status
# ---------------------------------------------------------------------------

class TestGithubOAuthStatus:
    def _login_and_get_state(self, client) -> str:
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "cid",
            "GITHUB_REDIRECT_URI": "http://localhost/cb",
        }):
            r = client.get("/github/login")
        return r.json()["state"]

    def test_pending_status_after_login(self, client):
        state = self._login_and_get_state(client)
        r = client.get(f"/github/oauth-status?state={state}")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_unknown_state_returns_404(self, client):
        r = client.get("/github/oauth-status?state=totally-made-up-state-xyz")
        assert r.status_code == 404
        assert r.json()["error_code"] == "BAD_OAUTH_STATE"

    def test_expired_state_returns_410(self, client):
        state = self._login_and_get_state(client)
        # Manually expire the state
        github_mod._oauth_states[state]["created_at"] = 0.0
        r = client.get(f"/github/oauth-status?state={state}")
        assert r.status_code == 410
        assert r.json()["error_code"] == "EXPIRED_OAUTH_STATE"

    def test_response_contains_state_field(self, client):
        state = self._login_and_get_state(client)
        r = client.get(f"/github/oauth-status?state={state}")
        assert r.json()["state"] == state

    def test_missing_state_param_returns_422(self, client):
        r = client.get("/github/oauth-status")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# PUT /github/revoke_access_token
# ---------------------------------------------------------------------------

class TestRevokeAccessToken:
    def test_revoke_success(self, client, blank_db):
        mock_config = MagicMock()
        mock_config.access_token = None  # after revocation

        with patch('src.interface.api.routers.github.get_most_recent_user_config') as mock_get_config, \
             patch('src.interface.api.routers.github.revoke_access_token') as mock_revoke, \
             patch('sqlmodel.Session.refresh'):
            mock_get_config.return_value = mock_config
            mock_revoke.return_value = mock_config
            r = client.put("/github/revoke_access_token")

        assert r.status_code == 200
        assert "revoked" in r.json()["message"].lower()

    def test_revoke_no_user_config_returns_404(self, client, blank_db):
        with patch('src.interface.api.routers.github.get_most_recent_user_config') as mock_get_config:
            mock_get_config.return_value = None
            r = client.put("/github/revoke_access_token")

        assert r.status_code == 404
        assert r.json()["error_code"] == "USER_CONFIG_NOT_FOUND"

    def test_revoke_db_failure_returns_500(self, client, blank_db):
        mock_config = MagicMock()
        mock_config.access_token = "still-set"  # revocation did not clear it

        with patch('src.interface.api.routers.github.get_most_recent_user_config') as mock_get_config, \
             patch('src.interface.api.routers.github.revoke_access_token') as mock_revoke:
            mock_get_config.return_value = mock_config
            mock_revoke.return_value = mock_config  # token NOT cleared
            r = client.put("/github/revoke_access_token")

        assert r.status_code == 500
        assert r.json()["error_code"] == "DATABASE_OPERATION_FAILED"
