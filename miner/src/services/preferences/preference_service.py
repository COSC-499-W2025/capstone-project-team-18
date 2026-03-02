"""
Service for updating preferences.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class UserConfig():
    # A data transfer object for user preferences
    consent: bool = False
    github: Optional[str] = None
    email: Optional[str] = None
    language_filter: Optional[list[str]] = None


def privacy_consent():
    # TODO
    pass
