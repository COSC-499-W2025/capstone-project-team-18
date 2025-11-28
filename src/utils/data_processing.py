"""
This file holds functions that help
with data processing.
"""

from typing import Any


def normalize(d: dict[Any, float]) -> None:
    """
    Normalize the values of a dictionary in place.

    Given a dictionary with arbitrary keys and float values, this function scales
    the values so that their sum becomes 1. To reduce floating-point error, the
    normalized values are rounded to five decimal places.

    The dict is assumed to only have positive values.

    Values may be all zero, and in this case the dictonary will be left
    unchanged.

    d : dict[Any, float]
        A dictionary whose float values will be normalized in place.

    None
        The dictionary is modified directly.
    """

    total = sum(d.values())

    if total == 0:
        # Do not divide by zero, leave dict unchanged
        return

    for k, v in d.items():
        d[k] = round(v / total, 5)
