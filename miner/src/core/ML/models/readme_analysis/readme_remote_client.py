"""
Compatibility shim for README remote extraction hooks.

This branch primarily uses Azure/OpenAI provider paths; when remote README
services are unavailable, these helpers return None so local/other fallbacks
can proceed.
"""

from __future__ import annotations


def remote_extract_keyphrases(_text: str, _top_n: int) -> list[str] | None:
    return None


def remote_extract_themes_bulk(_texts: list[str], _max_themes: int) -> list[list[str]] | None:
    return None
