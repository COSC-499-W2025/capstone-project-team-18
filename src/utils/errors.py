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
    SQL_MODEL_ERROR = "SQL_MODEL_ERROR"
    SQL_MODEL_CONVERSION_ERROR = "SQL_MODEL_CONVERSION_ERROR"
    SERIALIZATION_ERROR = "SERIALIZATION_ERROR"
    UNKNOWN_DESERIALIZATION_CLASS = "UNKNOWN_DESERIALIZATION_CLASS"
    UNHANDLE_VALUE = "UNHANDLE_VALUE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


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
