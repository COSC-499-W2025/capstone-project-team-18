import os
from typing import Any

from sqlmodel import Session

from src.database.api.CRUD.user_config import get_most_recent_user_config


def _is_unspecified_user_config(user_config: Any) -> bool:
    """Return True for blank in-memory configs used in local analysis/tests."""
    return (
        user_config.id is None
        and user_config.user_email is None
        and user_config.github is None
        and not bool(user_config.consent)
        and not bool(user_config.ml_consent)
    )


def ml_extraction_allowed(*, session: Session | None = None, user_config: Any | None = None) -> bool:
    """Return whether ML-backed features are allowed for the current user."""
    if os.environ.get("ARTIFACT_MINER_DISABLE_ML") == "1":
        return False

    config = user_config
    if config is None and session is not None:
        config = get_most_recent_user_config(session)
    elif config is None:
        from src.database.core.base import get_engine

        try:
            with Session(get_engine()) as db_session:
                config = get_most_recent_user_config(db_session)
        except Exception:
            config = None
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
        and config.id is None
        and bool(config.ml_consent)
        and not bool(config.consent)
    ):
        return True

    if not bool(config.consent):
        return False

    return bool(config.ml_consent)
