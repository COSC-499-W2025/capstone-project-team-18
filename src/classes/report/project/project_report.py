"""
This file defines the ProjectReport class
"""

from typing import Optional
from pathlib import Path
from git import Repo
from datetime import datetime, date

from src.classes.report.base_report import BaseReport
from src.classes.report.file_report import FileReport
from src.classes.statistic import StatisticIndex, ProjectStatCollection, FileStatCollection
from src.classes.resume.bullet_point_builder import BulletPointBuilder
from src.classes.resume.resume import ResumeItem


class ProjectReport(BaseReport):
    """
    The `ProjectReport` class utilizes many `FileReports` to
    create project-level statistics about a single project.

    For example, maybe we sum up all the lines of written
    in a `FileReport` to create a project level statistics
    of "total lines written."
    """

    bullet_builder = BulletPointBuilder()

    def __init__(self,
                 file_reports: Optional[list[FileReport]] = None,
                 project_path: Optional[str] = None,
                 project_name: Optional[str] = None,
                 user_email: Optional[str] = None,
                 statistics: Optional[StatisticIndex] = None,
                 project_repo: Optional[Repo] = None
                 ):
        """
        Initialize `ProjectReport` with file reports and optional Git analysis from zip file.

        Args:
            file_reports: List of FileReport objects to aggregate statistics from
            project_path: Optional path to project for Git analysis
            project_name: Optional project name for Git analysis
            statistics: Optional StatisicIndex
            project_repo: Optional Repo object for Git analysis
            user_email: Optional user email for Git authorship analysis

        NOTE: `statistics` should only be included when the `get_project_from_project_name()`
        function is creating a `ProjectReport` object from an existing row in
        the `project_report` table!
        """
        self.file_reports = file_reports or []
        self.project_name = project_name or "Unknown Project"
        self.project_path = project_path or "Unknown Path"
        self.project_repo = project_repo
        self.email = user_email
        self.sub_dirs = self._get_sub_dirs()

        self.project_statistics = StatisticIndex()

        # In this case, we are loading from the database and we are explicitly
        # given statistics. We load those stats in, and move on
        if statistics is not None:
            self.project_statistics = statistics
            super().__init__(self.project_statistics)
            return

        # Build statistics using the project statistic builder
        # Use a local import to avoid potential circular imports at module load time
        from src.classes.report.project.project_statistics import ProjectStatisticReportBuilder

        builder = ProjectStatisticReportBuilder()
        builder.build(self)

        # Initialize the base class with the project statistics
        super().__init__(self.project_statistics)

    def get_project_weight(self) -> float:
        """
        Ranks the project using a linear combination of lines of code, date range, and individual contribution.
        Equal weightage is given to each factor. All factors are normalized to [0, 1] scale.
        The returned value is the sum of the three normalized components, so the final score is in [0, 3].
        """
        # Lines normalization
        total_lines = 0.0
        if self.file_reports:
            total_lines = sum(
                report.get_value(FileStatCollection.LINES_IN_FILE.value) or 0.0
                for report in self.file_reports
            )
        norm_lines = min(total_lines / 500.0, 1.0) if total_lines > 0 else 0.0

        # Date range normalization (assume 1 year = 1.0 weight)
        start_date = self.get_value(
            ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = self.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
        norm_date = 0.0

        if isinstance(start_date, (datetime, date)) and isinstance(end_date, (datetime, date)):
            days = (end_date - start_date).days
            norm_date = min(days / 365, 1.0) if days > 0 else 0.0

        # Individual contribution normalization
        contrib = self.get_value(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)
        norm_contrib = 0.0
        if isinstance(contrib, (int, float)):
            norm_contrib = max(0.0, min(contrib / 100.0, 1.0))

        # Final weight (sum of normalized components)
        weight = norm_lines + norm_date + norm_contrib
        return weight

    def _get_sub_dirs(self) -> set[str]:
        """
        Get the sub directory of this project
        top level directory
        """

        root = Path(self.project_path)
        return {p.name for p in root.rglob('*') if p.is_dir()}

    def generate_resume_item(self) -> ResumeItem:
        """
        Generates a `ResumeItem` from the project report statistics.

        Args:
            title: Title of the resume item
            bullet_points: List of bullet points describing the project
            start_date: Start date of the project
            end_date: End date of the project
        """

        start_date = self.get_value(
            ProjectStatCollection.PROJECT_START_DATE.value)
        end_date = self.get_value(
            ProjectStatCollection.PROJECT_END_DATE.value)
        frameworks = self.get_value(
            ProjectStatCollection.PROJECT_FRAMEWORKS.value
        )

        bullet_points = self.bullet_builder.build(self)

        return ResumeItem(
            title=self.project_name,
            frameworks=frameworks if frameworks else [],
            bullet_points=bullet_points,
            start_date=start_date,
            end_date=end_date
        )
