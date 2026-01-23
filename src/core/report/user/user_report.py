"""
This file defines the UserReport class.
"""

from typing import Any, Optional
from pathlib import Path
from typing import Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.core.report.base_report import BaseReport
from src.core.report import ProjectReport
from src.core.statistic import (
    StatisticIndex,
    ProjectStatCollection,
    UserStatCollection,
    WeightedSkills,
    StatisticTemplate,
)
from src.core.resume.resume import Resume

from src.infrastructure.database.base import get_engine
from src.infrastructure.database.models import UserReportTable


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

    @staticmethod
    def delete_portfolio(identifier: str) -> tuple[bool, str]:
        """
        Delete a user report and its associated project reports from the database.

        Args:
            identifier: Either a portfolio title or filepath (extracts folder name from path)

        Returns:
            tuple: (success: bool, message: str)
        """
        from src.infrastructure.database.utils.database_modify import delete_user_report_and_related_data

        engine = get_engine()

        try:
            with Session(engine) as session:
                # Extract folder name from path if it's a path
                if '/' in identifier or '\\' in identifier:
                    folder_name = Path(identifier).stem
                else:
                    folder_name = identifier

                # Find by title to get project count before deletion
                stmt = select(UserReportTable).where(
                    UserReportTable.title == folder_name
                )
                user_report = session.scalar(stmt)

                if not user_report:
                    return False, f"Portfolio '{folder_name}' not found in database"

                # Store info for return message
                title = user_report.title
                project_count = len(user_report.project_reports)

            # Use database_modify function for deletion (outside the session)
            success = delete_user_report_and_related_data(title=title)

            if success:
                return True, f"Successfully deleted '{title}' and {project_count} associated project(s)"
            else:
                return False, f"Failed to delete portfolio '{title}' from database"

        except ValueError as e:
            # Handle "User report not found" from database_modify
            return False, str(e)
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def get_portfolio_info(identifier: str) -> tuple[bool, dict]:
        """
        Get information about a portfolio without deleting it.

        Args:
            identifier: Either a portfolio title or filepath (extracts folder name from path)

        Returns:
            tuple: (found: bool, info: dict with title and project_count)
        """

        engine = get_engine()

        try:
            with Session(engine) as session:
                # Extract folder name from path if it's a path
                if '/' in identifier or '\\' in identifier:
                    folder_name = Path(identifier).stem
                else:
                    folder_name = identifier

                # Find by title
                stmt = select(UserReportTable).where(
                    UserReportTable.title == folder_name
                )
                user_report = session.scalar(stmt)

                if not user_report:
                    return False, {}

                info = {
                    'title': user_report.title,
                    'project_count': len(user_report.project_reports)
                }

                return True, info

        except Exception:
            return False, {}

    @staticmethod
    def list_all_portfolios() -> list[dict]:
        """
        Get a list of all portfolios in the database.

        Returns:
            list: List of dicts with portfolio info (title, project_count)
        """

        engine = get_engine()

        try:
            with Session(engine) as session:
                # Force fresh query, don't use cache
                session.expire_all()

                stmt = select(UserReportTable)
                portfolios = session.scalars(stmt).all()

                portfolio_list = []
                for portfolio in portfolios:
                    portfolio_list.append({
                        'title': portfolio.title,
                        'project_count': len(portfolio.project_reports)
                    })

                return portfolio_list

        except Exception:
            return []

    @staticmethod
    def _fmt_mdy(d: datetime | date | None) -> str:
        if d is None:
            return "an unknown date"
        if isinstance(d, date) and not isinstance(d, datetime):
            d = datetime(d.year, d.month, d.day)
        return f"{d.month}/{d.day}/{d.year}"

    @staticmethod
    def _coerce_datetime(val: Any) -> datetime | None:
        """Coerce a value to datetime. Raises TypeError if value cannot be coerced."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime(val.year, val.month, val.day)
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val)
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%fZ"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    pass
            return datetime.fromisoformat(val)
        raise TypeError(f"Cannot coerce {type(val).__name__} to datetime")

    @staticmethod
    def _title_from_name(raw: str) -> str:
        s = raw.replace("_", " ").replace("-", " ").strip().lower().title()
        return s

    def to_user_readable_string(self) -> str:
        """
        Generate a user-readable portfolio using the portfolio builder system.
        This delegates to concrete builders for flexible, modular portfolio generation.
        """
        from src.core.portfolio.builder.concrete_builders import (
            UserStartDateSectionBuilder,
            UserEndDateSectionBuilder,
            UserSkillsSectionBuilder,
            UserCodingLanguageRatioSectionBuilder,
            UserGenericStatisticsSectionBuilder,
            ChronologicalProjectsSectionBuilder,
            ChronologicalSkillsSectionBuilder,
            ProjectTagsSectionBuilder,
            ProjectThemesSectionBuilder,
            ProjectTonesSectionBuilder,
        )
        from src.core.portfolio.builder.build_system import PortfolioBuilder
        
        # Create portfolio builder with all section builders
        builder = PortfolioBuilder()
        builder.register_section_builder(UserStartDateSectionBuilder())
        builder.register_section_builder(UserEndDateSectionBuilder())
        builder.register_section_builder(UserSkillsSectionBuilder())
        builder.register_section_builder(UserCodingLanguageRatioSectionBuilder())
        builder.register_section_builder(UserGenericStatisticsSectionBuilder())
        builder.register_section_builder(ChronologicalProjectsSectionBuilder())
        builder.register_section_builder(ChronologicalSkillsSectionBuilder())
        builder.register_section_builder(ProjectTagsSectionBuilder())
        builder.register_section_builder(ProjectThemesSectionBuilder())
        builder.register_section_builder(ProjectTonesSectionBuilder())
        
        # Build and render portfolio
        portfolio = builder.build(self)
        return portfolio.render()

    @staticmethod
    def _fmt_mdy_short(d: datetime | date | None) -> str:
        """Format as 'Mon D, YYYY' (e.g. 'Jan 12, 2023')."""
        if d is None:
            return "an unknown date"
        if isinstance(d, date) and not isinstance(d, datetime):
            d = datetime(d.year, d.month, d.day)
        return d.strftime("%b %d, %Y")

    def get_chronological_projects(
        self,
        as_string: bool = True,
        include_end_date: bool = False,
        newest_first: bool = False,
        numbered: bool = False,
    ) -> list[str] | str:
        """
        Return the user's projects ordered by start date.
        This implementation includes inclusion of start & end dates
        and numbering for both string and list outputs.
        """
        include_end_date = True
        numbered = True

        if not getattr(self, "project_reports", None):
            return "" if as_string else []

        entries: list[dict] = []
        for pr in self.project_reports:
            title = getattr(pr, "project_name", None) or "Untitled Project"
            start_dt = self._coerce_datetime(
                pr.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
            )
            end_dt = self._coerce_datetime(
                pr.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
            )

            if start_dt:
                formatted = f"{title} - Started {self._fmt_mdy_short(start_dt)}"
            else:
                formatted = f"{title} - Start date unknown"
            if end_dt:
                formatted += f" (Ended {self._fmt_mdy_short(end_dt)})"
            else:
                formatted += " (End date unknown)"

            entries.append(
                {"title": title, "start_date": start_dt, "formatted": formatted})

        dated = [e for e in entries if e["start_date"] is not None]
        undated = [e for e in entries if e["start_date"] is None]

        # Sort dated projects by start_date (oldest -> newest)
        dated.sort(key=lambda e: e["start_date"])
        if newest_first:
            dated.reverse()

        ordered = dated + undated

        # Build numbered lines (numbering always applied)
        lines = [f"{i+1}. {e['formatted']}" for i, e in enumerate(ordered)]

        if as_string:
            return "\n".join(lines)

        return lines

    def _project_stat_lines(
        self,
        template: StatisticTemplate,
        formatter,
        as_string: bool,
    ) -> list[str] | str:
        if not getattr(self, "project_reports", None):
            return "" if as_string else []

        lines: list[str] = []
        for pr in self.project_reports:
            value = pr.get_value(template)
            if not value:
                continue
            lines.append(f"{pr.project_name}: {formatter(value)}")

        if not lines:
            return "" if as_string else []

        return "\n".join(lines) if as_string else lines

    def get_project_tags(self, as_string: bool = True) -> list[str] | str:
        """
        Return a list of per-project tag lines:
            "Project Name: tag1, tag2, tag3"
        """
        return self._project_stat_lines(
            ProjectStatCollection.PROJECT_TAGS.value,
            lambda tags: ", ".join(tags),
            as_string,
        )

    def get_project_themes(self, as_string: bool = True) -> list[str] | str:
        """
        Return a list of per-project theme lines:
            "Project Name: theme1, theme2"
        """
        return self._project_stat_lines(
            ProjectStatCollection.PROJECT_THEMES.value,
            lambda themes: ", ".join(themes),
            as_string,
        )

    def get_project_tones(self, as_string: bool = True) -> list[str] | str:
        """
        Return a list of per-project tone lines:
            "Project Name: Professional"
        """
        return self._project_stat_lines(
            ProjectStatCollection.PROJECT_TONE.value,
            lambda tone: tone,
            as_string,
        )
