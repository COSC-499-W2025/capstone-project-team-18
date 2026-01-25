import os

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _load_cli_consent() -> bool | None:
    """Return consent from CLI preferences if available, else None."""
    try:
        from src.interface.cli.user_preferences import UserPreferences
    except Exception:
        return None

    try:
        return bool(UserPreferences().get("consent", False))
    except Exception:
        logger.debug("Failed to read CLI preferences for consent", exc_info=True)
        return None


def ml_extraction_allowed() -> bool:
    """
    Decide whether ML extraction should run.

    - Preferences consent is the primary gate when available.
    - Env flags provide an explicit override for non-interactive contexts.
    """
    if os.environ.get("ARTIFACT_MINER_DISABLE_ML") == "1":
        logger.info("ML extraction disabled via ARTIFACT_MINER_DISABLE_ML")
        return False

    consent = _load_cli_consent()
    if consent is False:
        logger.info("ML extraction disabled: consent not granted in preferences")
        return False

    return True
