"""
Defines the SQLModels for the database. Note these are also valid
returnable types for FastAPI
"""

import base64
from datetime import datetime, date
from typing import Optional, List, Any
from datetime import datetime
from pydantic import field_serializer
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON, LargeBinary


class UserConfigModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    consent: bool = Field(default=False)
    ml_consent: bool = Field(default=False)
    user_email: Optional[str] = None
    github: Optional[str] = None
    access_token: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now())

    # One-to-many relationship with ProjectReport
    project_reports: List["ProjectReportModel"] = Relationship(
        back_populates="user_config")

    # One-to-one relationship with ResumeConfigModel
    resume_config: Optional["ResumeConfigModel"] = Relationship(
        back_populates="user_config",
        sa_relationship_kwargs={
            "uselist": False, # Enforces 1-to-1
            "cascade": "all, delete-orphan"
            }
    )


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
    analyzed_count: int = Field(default=1, nullable=False)
    parent: Optional[str] = None

    # Representation (Milestone 2 human-in-the-loop)
    representation_rank: int | None = None
    chrono_start_override: datetime | None = None
    chrono_end_override: datetime | None = None
    showcase_selected: bool = Field(default=False)
    compare_attributes: List[str] = Field(
        sa_column=Column(JSON), default_factory=list)
    highlight_skills: List[str] = Field(
        sa_column=Column(JSON), default_factory=list)
    representation_last_user_edit_at: datetime | None = None

    # These fields allow users to override the auto-generated showcase portfolio
    showcase_title: Optional[str] = None
    showcase_start_date: Optional[datetime] = None
    showcase_end_date: Optional[datetime] = None
    showcase_frameworks: List[str] = Field(
        default_factory=list, sa_column=Column(JSON))
    showcase_bullet_points: List[str] = Field(
        default_factory=list, sa_column=Column(JSON))
    showcase_last_user_edit_at: Optional[datetime] = None

    # Relationships

    # Idea here is that user gets a warning if PR is outdate with current config
    user_config: Optional[UserConfigModel] = Relationship(
        back_populates="project_reports")
    file_reports: List["FileReportModel"] = Relationship(
        back_populates="project")
    project_insights: Optional["ProjectInsightsModel"] = Relationship(
        back_populates="project",
        cascade_delete=True)


class ProjectInsightsModel(SQLModel, table=True):
    project_name: str = Field(
        primary_key=True,
        foreign_key="projectreportmodel.project_name",
        ondelete="CASCADE"
    )
    insights: List[str] = Field(sa_column=Column(JSON, nullable=False))
    generated_at: datetime = Field(default_factory=lambda: datetime.now())

    # Relationship
    project: Optional["ProjectReportModel"] = Relationship(
        back_populates="project_insights")


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


class ResumeConfigModel(SQLModel, table=True):
    """
    Resume configuration that stores education and awards.
    Has a 1-to-1 relationship with UserConfigModel.
    This is global per user, not per resume.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key to UserConfigModel (1-to-1)
    user_config_id: Optional[int] = Field(
        default=None,
        foreign_key="userconfigmodel.id",
        unique=True  # Enforces 1-to-1
    )

    # Education entries (e.g., ["BSc Computer Science, UBC, 2024"])
    education: List[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=list
    )

    # Awards/honors (e.g., ["Dean's List 2023"])
    awards: List[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=list
    )

    # User-supplied skills (e.g., ["Python", "React"])
    skills: List[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=list
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now())
    last_updated: datetime = Field(default_factory=lambda: datetime.now())

    user_config: Optional["UserConfigModel"] = Relationship(back_populates="resume_config")

class ResumeModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    email: Optional[str] = None
    github: Optional[str] = None
    skills: List[str] = Field(sa_column=Column(JSON, nullable=False))

    # Store categorized skills as snapshot at gen/edit time
    skills_expert: List[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=list
    )
    skills_intermediate: List[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=list
    )
    skills_exposure: List[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=list
    )

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
    block_order: List[str] = Field(sa_column=Column(JSON), default=list())

    portfolio: Optional["PortfolioModel"] = Relationship(
        back_populates="sections")
    blocks: List["BlockModel"] = Relationship(back_populates="section")


class PortfolioModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str

    # Metadata fields
    creation_time: datetime = Field(default_factory=datetime.now)
    last_updated_at: datetime = Field(default_factory=datetime.now)
    project_ids_include: List[str] = Field(
        sa_column=Column(JSON), default=list())

    # Relationships
    sections: List["PortfolioSectionModel"] = Relationship(
        back_populates="portfolio")
    project_cards: List["PortfolioProjectCardModel"] = Relationship(
        back_populates="portfolio")


class PortfolioProjectCardModel(SQLModel, table=True):
    """
    Portfolio-scoped project card for the gallery (Part C) and showcase (Part B).

    Auto-populated fields are refreshed on portfolio regeneration.
    User override fields are preserved across refreshes.
    The is_showcase flag is user-controlled and never overwritten by the system.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfoliomodel.id")

    # project_name is NOT a FK — portfolio-scoped snapshot; avoids cascade issues
    project_name: str

    # Auto-populated from project statistics
    image_data: Optional[bytes] = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True))
    summary: str = Field(default="")
    themes: List[str] = Field(sa_column=Column(JSON), default_factory=list)
    tones: str = Field(default="")
    tags: List[str] = Field(sa_column=Column(JSON), default_factory=list)
    skills: List[str] = Field(sa_column=Column(JSON), default_factory=list)
    frameworks: List[str] = Field(sa_column=Column(JSON), default_factory=list)
    languages: dict = Field(sa_column=Column(JSON), default_factory=dict)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_group_project: bool = Field(default=False)
    collaboration_role: str = Field(default="")
    work_pattern: str = Field(default="")
    commit_type_distribution: dict = Field(
        sa_column=Column(JSON), default_factory=dict)
    activity_metrics: dict = Field(sa_column=Column(JSON), default_factory=dict)

    # Part B showcase flag — user-controlled, never overwritten by system on refresh
    is_showcase: bool = Field(default=False)

    # User-editable overrides — never overwritten by system on refresh
    title_override: Optional[str] = None
    summary_override: Optional[str] = None
    tags_override: Optional[List[str]] = Field(
        sa_column=Column(JSON), default=None)

    last_user_edit_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

    portfolio: Optional["PortfolioModel"] = Relationship(
        back_populates="project_cards")

    @field_serializer("image_data")
    def encode_image_data(self, value: Optional[bytes]) -> Optional[str]:
        if value is None:
            return None
        return base64.b64encode(value).decode("utf-8")
