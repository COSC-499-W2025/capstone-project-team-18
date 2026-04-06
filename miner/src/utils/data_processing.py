"""
This file holds functions that help
with data processing.
"""

from typing import Any
from datetime import datetime, date


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


def fmt_mdy_short(d: datetime | date | None) -> str:
    """Format as 'Mon D, YYYY' (e.g. 'Jan 12, 2023')."""
    if d is None:
        return "an unknown date"
    if isinstance(d, date) and not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day)
    return d.strftime("%b %d, %Y")


def join_english(items: list[str]) -> str:
    """Join a list of strings into natural English with commas and 'and'."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def fmt_mdy(d: datetime | date | None) -> str:
    if d is None:
        return "an unknown date"
    if isinstance(d, date) and not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day)
    return f"{d.month}/{d.day}/{d.year}"
