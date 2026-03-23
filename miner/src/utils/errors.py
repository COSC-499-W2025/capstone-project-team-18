"""
This gives us custom errors we can raise. This allows us
to catch errors in a type safe way, rather than trying to
switch based on string messages.
"""

from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for frontend/backend communication"""
    ID_NOT_FOUND = "ID_NOT_FOUND"
    NO_RELEVANT_FILES = "NO_RELEVANT_FILES"
    NO_DISCOVERED_PROJECTS = "NO_DISCOVERED_PROJECTS"
    MISSING_CONSENT = "MISSING_CONSENT"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SQL_MODEL_ERROR = "SQL_MODEL_ERROR"
    SQL_MODEL_CONVERSION_ERROR = "SQL_MODEL_CONVERSION_ERROR"
    SERIALIZATION_ERROR = "SERIALIZATION_ERROR"
    UNKNOWN_DESERIALIZATION_CLASS = "UNKNOWN_DESERIALIZATION_CLASS"
    UNHANDLE_VALUE = "UNHANDLE_VALUE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    RESUME_NOT_FOUND = "RESUME_NOT_FOUND"
    USER_CONFIG_NOT_FOUND = "USER_CONFIG_NOT_FOUND"
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"
    DATABASE_OPERATION_FAILED = "DATABASE_OPERATION_FAILED"
    BAD_OAUTH_STATE = "BAD_OAUTH_STATE"
    EXPIRED_OAUTH_STATE = "EXPIRED_OAUTH_STATE"


class KeyNotFoundError(Exception):
    """Can't find object in database with key"""
    error_code: ErrorCode = ErrorCode.ID_NOT_FOUND


class SerializationError(Exception):
    """Error with the serialization or deserialization process"""
    error_code: ErrorCode = ErrorCode.SERIALIZATION_ERROR


class UnkownDeserializationClass(SerializationError):
    """You tried to deserialize to an unkown class"""
    error_code: ErrorCode = ErrorCode.UNKNOWN_DESERIALIZATION_CLASS


class UnhandledValue(SerializationError):
    """You tried to deserialize a malformated or unkown value"""
    error_code: ErrorCode = ErrorCode.UNHANDLE_VALUE


class SQLModelError(Exception):
    """Errors that relate specifical to SQLModel"""
    error_code: ErrorCode = ErrorCode.SQL_MODEL_ERROR


class DomainClassToModelConverisonError(SQLModelError):
    """Tried to convert a domain class to a SQLModel"""
    error_code: ErrorCode = ErrorCode.SQL_MODEL_CONVERSION_ERROR


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


class ProjectNotFoundError(ArtifactMinerException):
    """A project could not be located in the database by the given name."""
    error_code = ErrorCode.PROJECT_NOT_FOUND


class ResumeNotFoundError(ArtifactMinerException):
    """A resume could not be located in the database by the given ID."""
    error_code = ErrorCode.RESUME_NOT_FOUND


class UserConfigNotFoundError(ArtifactMinerException):
    """The user configuration record could not be found."""
    error_code = ErrorCode.USER_CONFIG_NOT_FOUND


class AIServiceUnavailableError(ArtifactMinerException):
    """An Azure OpenAI-backed feature is not reachable or not configured."""
    error_code = ErrorCode.AI_SERVICE_UNAVAILABLE


class DatabaseOperationError(ArtifactMinerException):
    """A write or read operation against the database failed unexpectedly."""
    error_code = ErrorCode.DATABASE_OPERATION_FAILED


class BadOAuthStateError(ArtifactMinerException):
    """
    The OAuth state that is passed in when GitHub makes a request to the
    callback endpoint is invalid.
    """
    error_code = ErrorCode.BAD_OAUTH_STATE


class ExpiredOAuthState(ArtifactMinerException):
    """
    The OAuth state that is passed in when GitHub makes a request to the
    callback endpoint has expired.
    """
