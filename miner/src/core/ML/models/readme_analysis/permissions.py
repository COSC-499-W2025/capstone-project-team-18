import os
from typing import Any

from sqlmodel import Session


def _is_unspecified_user_config(user_config: Any) -> bool:
    """Return True for blank in-memory configs used in local analysis/tests."""
    return (
        getattr(user_config, "id", None) is None
        and getattr(user_config, "user_email", None) is None
        and getattr(user_config, "github", None) is None
        and not bool(getattr(user_config, "consent", False))
        and not bool(getattr(user_config, "ml_consent", False))
    )


def _load_current_user_config(
    *,
    session: Session | None = None,
    user_config: Any | None = None,
) -> Any | None:
    """Return the current user config when available."""
    if user_config is not None:
        return user_config

    from src.database import get_most_recent_user_config

    if session is not None:
        return get_most_recent_user_config(session)

    try:
        from src.database.core.base import get_engine

        with Session(get_engine()) as db_session:
            return get_most_recent_user_config(db_session)
    except Exception:
        return None


def ml_extraction_allowed(*, session: Session | None = None, user_config: Any | None = None) -> bool:
    """Return whether ML-backed features are allowed for the current user."""
    if os.environ.get("ARTIFACT_MINER_DISABLE_ML") == "1":
        return False

    config = _load_current_user_config(session=session, user_config=user_config)
    if config is None:
        return session is None and user_config is None

    if user_config is not None and _is_unspecified_user_config(config):
        return True

    # Test/local analyzers often pass an unsaved in-memory config with only
    # ml_consent toggled on. Treat that as opt-in for local extraction while
    # keeping persisted/session-backed request flows strict.
    if (
        user_config is not None
        and session is None
        and getattr(config, "id", None) is None
        and bool(getattr(config, "ml_consent", False))
        and not bool(getattr(config, "consent", False))
    ):
        return True

    if not bool(getattr(config, "consent", False)):
        return False

    return bool(getattr(config, "ml_consent", False))
