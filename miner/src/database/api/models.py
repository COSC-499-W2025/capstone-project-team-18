"""
Defines the SQLModels for the database. Note these are also valid
returnable types for FastAPI
"""

from datetime import datetime, date
from typing import Optional, List, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON, LargeBinary


class UserConfigModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    consent: bool = Field(default=False)
    user_email: Optional[str] = None
    github: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now())

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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now())
    last_updated: datetime = Field(default_factory=lambda: datetime.now())

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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now())

    # Relationship
    project: Optional[ProjectReportModel] = Relationship(
        back_populates="file_reports")


class ResumeModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = None
    github: Optional[str] = None
    skills: List[str] = Field(sa_column=Column(JSON, nullable=False))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now())
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now())

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

    created_at: datetime = Field(
        default_factory=lambda: datetime.now())
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now())

    # Relationship
    resume: Optional[ResumeModel] = Relationship(back_populates="items")


class BlockModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    section_id: Optional[int] = Field(
        default=None, foreign_key="portfoliosectionmodel.id")

    tag: str
    content_type: str

    # Metadata
    last_generated_at: Optional[datetime] = None
    last_user_edit_at: Optional[datetime] = None
    in_conflict: bool = Field(default=False)

    # Content as JSON
    current_content: Any = Field(sa_column=Column(JSON))
    conflict_content: Optional[Any] = Field(
        sa_column=Column(JSON), default=None)

    section: Optional["PortfolioSectionModel"] = Relationship(
        back_populates="blocks")


class PortfolioSectionModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: Optional[int] = Field(
        default=None, foreign_key="portfoliomodel.id")

    section_id: str
    title: str
    order: int = 0
    block_order: List[str] = Field(sa_column=Column(JSON), default=[])

    portfolio: Optional["PortfolioModel"] = Relationship(
        back_populates="sections")
    blocks: List["BlockModel"] = Relationship(back_populates="section")


class PortfolioModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str

    # Metadata fields
    creation_time: datetime = Field(default_factory=datetime.now)
    last_updated_at: datetime = Field(default_factory=datetime.now)
    project_ids_include: List[str] = Field(sa_column=Column(JSON), default=[])

    # Relationships
    sections: List["PortfolioSectionModel"] = Relationship(
        back_populates="portfolio")
