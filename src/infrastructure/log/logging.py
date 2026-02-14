"""
This file handles all logic for logging
"""

import logging


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
