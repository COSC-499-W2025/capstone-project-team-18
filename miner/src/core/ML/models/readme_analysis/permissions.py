import os
from typing import Any

from sqlmodel import Session

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _load_db_ml_consent(session: Session | None = None) -> bool | None:
    """Return ML consent from UserConfig when the database is reachable."""
    try:
        from src.database import get_most_recent_user_config
    except Exception:
        return None

    try:
        if session is not None:
            config = get_most_recent_user_config(session)
            return bool(getattr(config, "ml_consent", False))

        from src.database.core.base import get_engine

        with Session(get_engine()) as db_session:
            config = get_most_recent_user_config(db_session)
            return bool(getattr(config, "ml_consent", False))
    except Exception:
        logger.debug("Failed to read UserConfig ML consent", exc_info=True)
        return None


def _load_cli_consent() -> bool | None:
    """Return ML consent from CLI preferences if available, else None."""
    try:
        from src.interface.cli.user_preferences import UserPreferences
    except Exception:
        return None

    try:
        preferences = UserPreferences()
        if preferences.get("ml_consent") is not None:
            return bool(preferences.get("ml_consent", False))
        return bool(preferences.get("consent", False))
    except Exception:
        logger.debug("Failed to read CLI preferences for ML consent", exc_info=True)
        return None


def ml_extraction_allowed(*, session: Session | None = None, user_config: Any | None = None) -> bool:
    """Return whether ML-backed features are allowed for the current user."""
    if os.environ.get("ARTIFACT_MINER_DISABLE_ML") == "1":
        logger.info("ML extraction disabled via ARTIFACT_MINER_DISABLE_ML")
        return False

    if user_config is not None and hasattr(user_config, "ml_consent"):
        consent = bool(getattr(user_config, "ml_consent", False))
        if not consent:
            logger.info("ML extraction disabled: consent not granted in UserConfig")
        return consent

    consent = _load_db_ml_consent(session)
    if consent is not None:
        if not consent:
            logger.info("ML extraction disabled: consent not granted in UserConfig")
        return consent

    consent = _load_cli_consent()
    if consent is not None:
        if not consent:
            logger.info("ML extraction disabled: consent not granted in preferences")
        return consent

    logger.info("ML extraction disabled: no ML consent was found")
    return False
