"""
This gives us custom errors we can raise. This allows us
to catch errors in a type safe way, rather than trying to
switch based on string messages.
"""


class NoDiscoveredProjects(Exception):
    """
    During the project discovery step, no
    projects were found.
    """
    pass


class ConsentError(Exception):
    """
    Errors to do with consent.
    """
    pass


class MissingStartMinerConsent(Exception):
    """
    A user has not consented to start
    the miner function.
    """
    pass
