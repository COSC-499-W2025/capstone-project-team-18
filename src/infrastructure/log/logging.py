"""
This file handles all logic for logging
"""

import logging
from pathlib import Path

# Create a new logfile with timestamp each time the program runs

LOG_FILE = Path(__file__).parent / "app.log"


def get_logger(name: str, level=logging.INFO):
    """
    Function to return a configured logging object.

    :param name: The name of the logger. Should always be __name__ of the calling file
    :type name: str
    :param level: The level the logger should log at
    """

    logger = logging.getLogger(name)

    # Disable logging globally for this application logger factory.
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    logger.setLevel(logging.CRITICAL + 1)
    return logger


def clear_logs() -> None:
    """Remove existing log files (base and rotated) to start fresh."""
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
        for idx in range(1, 5):
            rotated = LOG_FILE.with_suffix(LOG_FILE.suffix + f".{idx}")
            if rotated.exists():
                rotated.unlink()
    except OSError:
        # Best-effort cleanup; logging will still work if deletion fails.
        pass
