"""
This file defines the UserReport class.
"""

from typing import Optional

from src.core.report.base_report import BaseReport
from src.core.report import ProjectReport
from src.core.statistic import (
    StatisticIndex,
    UserStatCollection,
)
from src.core.resume.resume import Resume
from src.core.portfolio.builder.build_system import PortfolioBuilder


class UserReport(BaseReport):
    """
    This UserReport class hold Statistics about the user. It is made
    from many different ReportReports
    """

    def __init__(self, project_reports: list[ProjectReport], report_name: str, statistics: Optional[StatisticIndex] = None):
        """
        Initialize UserReport with project reports to calculate user-level statistics.

        This method calculates user-level statistics by finding:
        - User start date: earliest project start date across all projects
        - User end date: latest project end date across all projects

        Args:
            project_reports (list[ProjectReport]): List of ProjectReport objects containing project-level statistics
            report_name (str): By default, the name of the zipped directory. Can be overwritten by user input
            statistics: Optional `StatisticIndex` when rebuilding `UserReport` from DB row
        """

        self.report_name = report_name
        self.project_reports = project_reports or []

        # In this case, we are loading from the database and we are explicitly
        # given statistics. We load those stats in, and move on
        if statistics is not None:
            super().__init__(statistics)
            return

        # rank the project reports according to their weights
        ranked_project_reports = sorted(
            project_reports, key=lambda p: p.get_project_weight(), reverse=True)

        self.resume_items = [report.generate_resume_item()
                             for report in ranked_project_reports]

        super().__init__(StatisticIndex())  # list of user-level statistics

        from src.core.report.user.user_statistics import UserStatisticReportBuilder

        builder = UserStatisticReportBuilder()
        builder.build(self)

    def generate_resume(self, email: Optional[str], github: Optional[str]) -> Resume:
        """
        Generates a Resume object based on the ResumeItem
        that are generated from the ProjectReports. As well
        as adding skills from the User Statistics.
        """

        weighted_skills = self.statistics.get_value(
            UserStatCollection.USER_SKILLS.value)

        resume = Resume(email, github, weighted_skills)

        for item in self.resume_items:
            resume.add_item(item)

        return resume

    def generate_portfolio(self, section_builders: Optional[list[type]] = None, portfolio_title: Optional[str] = None):
        """
        Generate a portfolio using the portfolio builder system.
        This delegates to concrete builders for flexible, modular portfolio generation.
        """
        from src.core.portfolio.builder.concrete_builders import (
            UserSummarySectionBuilder,
            UserSkillsSectionBuilder,
            UserCodingLanguageRatioSectionBuilder,
            UserGenericStatisticsSectionBuilder,
            ChronologicalProjectsSectionBuilder,
            ProjectSummariesSectionBuilder,
            ProjectTagsSectionBuilder,
            ProjectThemesSectionBuilder,
            ProjectTonesSectionBuilder,
            ProjectActivityMetricsSectionBuilder,
            ProjectCommitFocusSectionBuilder,
        )

        builder = PortfolioBuilder()

        if section_builders:
            # Case we want to include only limited amount of sections
            for section_builder in section_builders:
                builder.register_section_builder(section_builder())
        else:
            # Case we want to include every section
            builder.register_section_builder(UserSummarySectionBuilder())
            builder.register_section_builder(UserSkillsSectionBuilder())
            builder.register_section_builder(
                UserCodingLanguageRatioSectionBuilder())
            builder.register_section_builder(
                UserGenericStatisticsSectionBuilder())
            builder.register_section_builder(
                ChronologicalProjectsSectionBuilder())
            builder.register_section_builder(ProjectSummariesSectionBuilder())
            builder.register_section_builder(ProjectTagsSectionBuilder())
            builder.register_section_builder(ProjectThemesSectionBuilder())
            builder.register_section_builder(ProjectTonesSectionBuilder())
            builder.register_section_builder(
                ProjectActivityMetricsSectionBuilder())
            builder.register_section_builder(
                ProjectCommitFocusSectionBuilder())

        return builder.build(self)

    def to_user_readable_string(self, section_builders: Optional[list[type]] = None) -> str:
        """
        Generate a user-readable portfolio.
        """

        return self.generate_portfolio(section_builders).render()
