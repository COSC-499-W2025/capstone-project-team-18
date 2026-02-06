"""
Defines the SQLModels for the database. Note these are also valid
returnable types for FastAPI
"""

from datetime import datetime, date
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON, LargeBinary


class UserConfigModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    consent: bool = Field(default=False)
    user_email: Optional[str] = None
    github: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # One-to-many relationship with ProjectReport
    project_reports: List["ProjectReportModel"] = Relationship(
        back_populates="user_config")


class ProjectReportModel(SQLModel, table=True):
    project_name: str = Field(primary_key=True)
    user_config_used: Optional[int] = Field(
        default=None, foreign_key="userconfigmodel.id")
    image_data: Optional[bytes] = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )  # This stores your image bytes
    statistic: dict = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Relationships

    # Idea here is that user gets a warning if PR is outdate with current config
    user_config: Optional[UserConfigModel] = Relationship(
        back_populates="project_reports")
    file_reports: List["FileReportModel"] = Relationship(
        back_populates="project")


class FileReportModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_name: str = Field(foreign_key="projectreportmodel.project_name")
    file_path: str
    is_info_file: bool = False
    file_hash: Optional[bytes] = None
    statistic: dict = Field(sa_column=Column(JSON, nullable=False))
    created_at: int = Field(
        default_factory=lambda: int(datetime.now().timestamp()))

    # Relationship
    project: Optional[ProjectReportModel] = Relationship(
        back_populates="file_reports")


class ResumeModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = None
    github: Optional[str] = None
    skills: List[str] = Field(sa_column=Column(JSON, nullable=False))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    items: List["ResumeItemModel"] = Relationship(back_populates="resume")


class ResumeItemModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    resume_id: Optional[int] = Field(
        default=None, foreign_key="resumemodel.id")

    project_name: Optional[str] = Field(
        default=None,
        foreign_key="projectreportmodel.project_name"
    )

    title: str
    frameworks: List[str] = Field(sa_column=Column(JSON, nullable=False))
    bullet_points: List[str] = Field(sa_column=Column(JSON, nullable=False))

    start_date: date
    end_date: date

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    resume: Optional[ResumeModel] = Relationship(back_populates="items")
