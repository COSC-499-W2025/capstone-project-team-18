from sqlmodel import Session, select
from typing import Optional
from sqlmodel import Session
from src.core.report.file_report import FileReport
from src.database.api.models import FileReportModel
from src.database.core.base import table_exists
from src.database.core.model_deserializer import deserialize_file_report


def get_file_report_model_by_hash(
        session: Session,
        hash: bytes
) -> Optional[FileReportModel]:
    if not table_exists('filereportmodel', session.get_bind()):
        return None

    statement = select(FileReportModel).where(
        FileReportModel.file_hash == hash)
    return session.exec(statement).first()


def get_file_report_by_hash(
        session: Session,
        hash: bytes
) -> Optional[FileReport]:
    """
    Retrieve a FileReportModel by its hash value, including all related statistics

    Args:
        session: SQLModel Session
        hash: The MD-5 hash to query

    Returns:
        FileReport object if found, else None
    """
    if not table_exists('filereportmodel', session.get_bind()):
        return None

    result = get_file_report_model_by_hash(session, hash)

    if result is None:
        return None

    return deserialize_file_report(result)


def delete_file_report_by_hash(
        session: Session,
        hash: bytes) -> bool:
    """Delete associated FileReport with hash that has changed since last analysis
    DOES NOT COMMIT THE SESSION! YOU MUST COMMIT.

    Args:
        session: SQLModel Session
        hash: The MD-5 hash of associated file_report

    Returns:
        True if a record was deleted, False if not found.
    """
    if not table_exists('filereportmodel', session.get_bind()):
        return False

    statement = select(FileReportModel).where(
        FileReportModel.file_hash == hash
    )

    current_file_report_model = session.exec(statement).first()

    if current_file_report_model is None:
        return False

    session.delete(current_file_report_model)
    return True


def filepath_exists_in_db(
        session: Session,
        filepath: str
) -> bool:
    """Lightwight check for filepath in database to be checked prior to hashing"""
    if not table_exists('filereportmodel', session.get_bind()):
        return False

    statement = select(FileReportModel).where(
        FileReportModel.file_path == filepath)

    return session.exec(statement).first() is not None
