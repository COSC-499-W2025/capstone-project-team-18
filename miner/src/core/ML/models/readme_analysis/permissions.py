import os
from sqlmodel import Session

from src.database.api.CRUD.user_config import get_most_recent_user_config


def ml_extraction_allowed(session: Session | None = None) -> bool:
    """Return whether ML-backed features are allowed for the current user."""
    if os.environ.get("ARTIFACT_MINER_DISABLE_ML") == "1":
        return False

    config = None
    if session is not None:
        config = get_most_recent_user_config(session)
    else:
        from src.database.core.base import get_engine

        try:
            with Session(get_engine()) as db_session:
                config = get_most_recent_user_config(db_session)
        except Exception:
            config = None

    if config is None:
        return session is None

    if not config.consent:
        return False

    return config.ml_consent
