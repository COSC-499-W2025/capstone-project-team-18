import os
from typing import Any

from sqlmodel import Session


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
        return False

    if not bool(getattr(config, "consent", False)):
        return False

    return bool(getattr(config, "ml_consent", False))
