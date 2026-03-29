"""
Shared Git utility helpers.
"""

import re


def is_github_noreply(email: str, github_username: str) -> bool:
    """Return True iff email is a known GitHub noreply address for github_username.

    GitHub uses two formats:
      {username}@users.noreply.github.com                    (old)
      {numeric_id}+{username}@users.noreply.github.com       (new)
    """
    domain = "users.noreply.github.com"
    if email == f"{github_username}@{domain}":
        return True
    return bool(re.match(rf"^\d+\+{re.escape(github_username)}@{re.escape(domain)}$", email))
