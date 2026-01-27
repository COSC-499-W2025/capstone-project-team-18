"""
This file defines the UserReport class.
"""

from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.core.report.base_report import BaseReport
from src.core.report import ProjectReport
from src.core.statistic import (
    StatisticIndex,
    UserStatCollection,
)
from src.core.resume.resume import Resume

from src.database.base import get_engine
from src.database.models import UserReportTable


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
        from src.database.utils.database_modify import delete_user_report_and_related_data

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
    def _format_limited_list(items: list[str], max_items: int) -> str:
        """Format a list with a max length, sorted for deterministic output."""
        if max_items <= 0:
            return ""
        sorted_items = sorted(items, key=lambda s: s.lower())
        return ", ".join(sorted_items[:max_items])

    @staticmethod
    def _get_user_pref_int(key: str, default: int) -> int:
        """Best-effort read of a user preference integer; fall back to default."""
        try:
            from src.interface.cli.user_preferences import UserPreferences
        except Exception:
            return default

        try:
            value = UserPreferences().get(key, default)
            if isinstance(value, bool):
                return default
            if isinstance(value, (int, float)) and int(value) > 0:
                return int(value)
            if isinstance(value, str) and value.strip().isdigit():
                parsed = int(value.strip())
                return parsed if parsed > 0 else default
        except Exception:
            return default

        return default

    def to_user_readable_string(self) -> str:
        """
        Generate a user-readable portfolio using the portfolio builder system.
        This delegates to concrete builders for flexible, modular portfolio generation.
        """
        from src.core.portfolio.builder.concrete_builders import (
            UserSkillsSectionBuilder,
            UserCodingLanguageRatioSectionBuilder,
            UserGenericStatisticsSectionBuilder,
            ChronologicalProjectsSectionBuilder,
            ProjectTagsSectionBuilder,
            ProjectThemesSectionBuilder,
            ProjectTonesSectionBuilder,
        )
        from src.core.portfolio.builder.build_system import PortfolioBuilder

        # Create portfolio builder with all section builders
        builder = PortfolioBuilder()
        builder.register_section_builder(UserSkillsSectionBuilder())
        builder.register_section_builder(
            UserCodingLanguageRatioSectionBuilder())
        builder.register_section_builder(UserGenericStatisticsSectionBuilder())
        builder.register_section_builder(ChronologicalProjectsSectionBuilder())
        builder.register_section_builder(ProjectTagsSectionBuilder())
        builder.register_section_builder(ProjectThemesSectionBuilder())
        builder.register_section_builder(ProjectTonesSectionBuilder())

        # Build and render portfolio
        portfolio = builder.build(self)
        return portfolio.render()

    def to_user_readable_string(self) -> str:
        """
        For every statistic in self.statistics, return a human-readable line.
        Known user stats get custom phrasing; others fall back to 'Title: value'.
        """
        if self.statistics is None or len(self.statistics) == 0:
            return "No user statistics are available yet."

        lines: list[str] = []

        for stat in self.statistics:
            template = stat.get_template()
            name = template.name
            value = stat.value

            if name == UserStatCollection.USER_START_DATE.value.name:
                dt = self._coerce_datetime(value)
                lines.append(
                    f"You started your first project on {self._fmt_mdy(dt)}!"
                )
                continue

            if name == UserStatCollection.USER_END_DATE.value.name:
                dt = self._coerce_datetime(value)
                lines.append(
                    f"Your latest contribution was on {self._fmt_mdy(dt)}."
                )
                continue

            if name == UserStatCollection.USER_SKILLS.value.name:
                skills_line = "an unknown set of skills"
                try:
                    if isinstance(value, list) and value:
                        def _skill_str(ws: WeightedSkills) -> str:
                            n = getattr(ws, "skill_name", None) or str(ws)
                            w = getattr(ws, "weight", None)
                            return f"{n}"
                        skills_line = ", ".join(_skill_str(ws)
                                                for ws in value[:15])
                except Exception:
                    pass
                lines.append(f"Your skills include: {skills_line}.")
                continue

            title = self._title_from_name(name)

            # Try to print the user's coding languages and its percent relative to all coding languages from the user
            if name == UserStatCollection.USER_CODING_LANGUAGE_RATIO.value.name:
                ratio_line = "coding languages not found"
                try:
                    lang_ratios = value
                    langs_sorted = sorted(
                        lang_ratios.items(), key=lambda x: x[1], reverse=True)
                    parts: list[str] = []
                    for lang, ratio in langs_sorted:
                        lang_name = lang.value
                        percent = f"{ratio * 100:.2f}%"
                        parts.append(f"{lang_name} ({percent})")
                except Exception:
                    ratio_line = "coding languages not found"
                ratio_line = f"Your coding languages: {', '.join(parts)}."
                lines.append(ratio_line)
                continue

            should_try_date = (
                template.expected_type in (date, datetime)
                or isinstance(value, (date, datetime))
                or isinstance(value, str)
            )
            maybe_dt = self._coerce_datetime(
                value) if should_try_date else None

            if maybe_dt:
                lines.append(f"{title}: {self._fmt_mdy(maybe_dt)}")
            else:
                lines.append(f"{title}: {value!r}")

        # Add chronological projects]
        projects_str = self.get_chronological_projects(as_string=True)
        if projects_str:
            lines.append("\nProjects in chronological order:")
            lines.append(projects_str)

        # Add chronological skills
        skills_str = self.get_chronological_skills(as_string=True)
        if skills_str:
            lines.append("\nSkills in chronological order:")
            lines.append(skills_str)

        # Add project tags
        tags_str = self.get_project_tags(as_string=True)
        if tags_str:
            lines.append("\nProject tags:")
            lines.append(tags_str)

        themes_str = self.get_project_themes(as_string=True)
        if themes_str:
            lines.append("\nProject themes:")
            lines.append(themes_str)

        tones_str = self.get_project_tones(as_string=True)
        if tones_str:
            lines.append("\nProject tone:")
            lines.append(tones_str)

       # Collaboration role
        role_lines = self.get_project_roles(as_string=True)
        if role_lines:
            lines.append("\nProject roles:")
            lines.append(role_lines)

        # Work pattern
        work_lines = self.get_project_work_patterns(as_string=True)
        if work_lines:
            lines.append("\nWork patterns:")
            lines.append(work_lines)

        # Activity metrics
        activity_lines = self.get_project_activity_metrics(as_string=True)
        if activity_lines:
            lines.append("\nActivity cadence:")
            lines.append(activity_lines)

        # Commit type distribution
        dist_lines = self.get_project_commit_focus(as_string=True)
        if dist_lines:
            lines.append("\nCommit focus:")
            lines.append(dist_lines)

        return "\n".join(lines)

    def get_project_roles(self, as_string: bool = True) -> list[str] | str:
        """
        Return a list of per-project collaboration roles:
            "Project Name: Leader"
        """
        return self._project_stat_lines(
            ProjectStatCollection.COLLABORATION_ROLE.value,
            lambda role: str(role).replace("_", " ").title(),
            as_string,
        )

    def get_project_work_patterns(self, as_string: bool = True) -> list[str] | str:
        """
        Return a list of per-project work patterns:
            "Project Name: Consistent"
        """
        return self._project_stat_lines(
            ProjectStatCollection.WORK_PATTERN.value,
            lambda pattern: str(pattern).replace("_", " ").title(),
            as_string,
        )

    def get_project_activity_metrics(self, as_string: bool = True) -> list[str] | str:
        """
        Return a list of per-project activity metrics:
            "Project Name: 5.2 commits/week, consistency 0.85"
        """
        def _fmt_activity(val: dict) -> str:
            cpw = val.get("avg_commits_per_week")
            cons = val.get("consistency_score")
            parts = []
            if cpw is not None:
                parts.append(f"{cpw:.1f} commits/week")
            if cons is not None:
                parts.append(f"consistency {cons:.2f}")
            return ", ".join(parts) if parts else "activity data unavailable"

        return self._project_stat_lines(
            ProjectStatCollection.ACTIVITY_METRICS.value,
            _fmt_activity,
            as_string,
        )

    def get_project_commit_focus(self, as_string: bool = True) -> list[str] | str:
        """
        Return a list of per-project commit type distributions:
            "Project Name: Feature 45%, Bugfix 30%, Documentation 25%"
        """
        def _fmt_commit_dist(val: dict) -> str:
            if not val:
                return "no commit data"
            top = sorted(val.items(), key=lambda kv: kv[1], reverse=True)
            return ", ".join(f"{k.title()} {v:.0f}%" for k, v in top if v > 0)

        return self._project_stat_lines(
            ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value,
            _fmt_commit_dist,
            as_string,
        )
