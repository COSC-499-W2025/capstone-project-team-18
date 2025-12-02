"""
This file holds functions that help
with data processing.
"""

from typing import Any


def normalize(d: dict[Any, float]) -> None:
    """
    Normalize the values of a dictionary in place.

    Given a dictionary with arbitrary keys and float values, this function scales
    the values so that their sum becomes 1.

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
        d[k] = v / total


def float_to_percent(f: float) -> str:
    """
    Takes a float f in [0,1] and returns
    a percent that is rounded to one decmial
    point for text formatting. (e.g. 0.76352 ->
    76%, 0.01733 -> 2%, 0.0002 -> ~0%)

    Throws error if float is not in [0,1]. Use
    carefully.

    """

    if not (0 <= f and f <= 1):
        raise ValueError("Float f not between interval [0,1]")

    f_rounded = round(f * 100)

    percent_str = f"{str(f_rounded)}%"

    if f_rounded == 0:
        return "~" + percent_str

    return percent_str
