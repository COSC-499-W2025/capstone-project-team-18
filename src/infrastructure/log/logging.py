"""
This file handles all logic for logging
"""

import logging
from pathlib import Path

from logging.handlers import RotatingFileHandler

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
    logger.setLevel(level)

    # Prevent logs from going to the terminal
    logger.propagate = False

    # Avoid adding multiple handlers if logger already has them
    if not logger.handlers:

        fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
        fh.setLevel(level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        fh.setFormatter(formatter)
        logger.addHandler(fh)

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
