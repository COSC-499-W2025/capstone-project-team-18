"""
This gives us custom errors we can raise. This allows us
to catch errors in a type safe way, rather than trying to
switch based on string messages.
"""

from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for frontend/backend communication"""
    NO_RELEVANT_FILES = "NO_RELEVANT_FILES"
    NO_DISCOVERED_PROJECTS = "NO_DISCOVERED_PROJECTS"
    MISSING_CONSENT = "MISSING_CONSENT"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    ALEMBIC_ERROR = "ALMEBIC_ERROR"
    ALEMBIC_MIGRATION_ERROR = "ALEMBIC_MIGRATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class AlembicError(Exception):
    """Alembic database error"""
    error_code: ErrorCode = ErrorCode.ALEMBIC_ERROR


class AlembicMigrationError(AlembicError):
    """Alembic Migration database error"""
    error_code: ErrorCode = ErrorCode.ALEMBIC_MIGRATION_ERROR


class ArtifactMinerException(Exception):
    """Base exception class with error code"""
    error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR


class NoDiscoveredProjects(ArtifactMinerException):
    """
    During the project discovery step, no
    projects were found.
    """
    error_code = ErrorCode.NO_DISCOVERED_PROJECTS


class NoRevelantFiles(ArtifactMinerException):
    """
    During project analysis, there were no
    files to be analyzed. This could be because
    the project has only junk config files, or
    because the user never commited to the project.
    """
    error_code = ErrorCode.NO_RELEVANT_FILES


class ConsentError(ArtifactMinerException):
    """
    Errors to do with consent.
    """
    pass


class MissingStartMinerConsent(ArtifactMinerException):
    """
    A user has not consented to start
    the miner function.
    """
    error_code = ErrorCode.MISSING_CONSENT
