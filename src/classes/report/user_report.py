"""
This file defines the UserReport class.
"""

from typing import Any, Optional
from pathlib import Path
from typing import Any
from datetime import datetime, date, timedelta, MINYEAR
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.classes.report.base_report import BaseReport
from src.classes.report.project_report import ProjectReport
from src.classes.statistic import Statistic, StatisticIndex, ProjectStatCollection, FileStatCollection, UserStatCollection, WeightedSkills
from src.classes.resume.resume import Resume


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
            self.user_stats = statistics
            super().__init__(self.user_stats)
            return

        # rank the project reports according to their weights
        ranked_project_reports = sorted(
            project_reports, key=lambda p: p.get_project_weight(), reverse=True)

        self.resume_items = [report.generate_resume_item()
                             for report in ranked_project_reports]

        self.user_stats = StatisticIndex()  # list of user-level statistics

        # Function calls to generate statistics
        self._determine_start_end_dates()
        self._find_coding_languages_ratio()
        self._weight_skills()

    def _weight_skills(self):
        """
        Calculates the user level stat of USER_SKILLS.

        We do this by lopping through a project level skills.
        The weight of a user skill, is the project level weight
        multiplied by the projects weight score.
        """

        users_skills = {}
        user_weighted_skills = []

        for project in self.project_reports:

            project_weighted_skills = project.statistics.get_value(
                ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

            if project_weighted_skills is None:
                continue

            for weighted_skill in project_weighted_skills:
                # If already a user skill, get weight
                prev_weight = users_skills.get(weighted_skill.skill_name, 0)

                # Add the weight and skill name to user_skills
                users_skills[weighted_skill.skill_name] = prev_weight + \
                    weighted_skill.weight * project.get_project_weight()

        for skill_name in users_skills.keys():
            user_weighted_skills.append(
                WeightedSkills(
                    skill_name=skill_name,
                    weight=users_skills[skill_name]
                )
            )

        self.add_statistic(
            Statistic(UserStatCollection.USER_SKILLS.value,
                      user_weighted_skills)
        )

    def _determine_start_end_dates(self):
        # Loop through and find the earliest start date and latest end date of all projects
        latest_date = datetime.now() + timedelta(days=1)  # 1 day in the future
        earliest_date = datetime(MINYEAR, 1, 1, 0, 0, 0, 0)
        # For checking that the time range is valid
        start_date = latest_date
        end_date = earliest_date
        for pr in self.project_reports:
            curr_start_date = self._coerce_datetime(
                pr.get_value(
                    ProjectStatCollection.PROJECT_START_DATE.value)
            )
            curr_end_date = self._coerce_datetime(
                pr.get_value(ProjectStatCollection.PROJECT_END_DATE.value)
            )
            if curr_start_date is not None and curr_start_date < start_date:
                start_date = curr_start_date
            if curr_end_date is not None and curr_end_date > end_date:
                end_date = curr_end_date
            # Make sure that the values were actually updated
            if start_date != latest_date:
                user_start_stat = Statistic(
                    UserStatCollection.USER_START_DATE.value, start_date)
                self.user_stats.add(user_start_stat)
            if end_date != earliest_date:
                user_end_stat = Statistic(
                    UserStatCollection.USER_END_DATE.value, end_date)
                self.user_stats.add(user_end_stat)

        # Initialize the base class with the user statistics
        super().__init__(self.user_stats)

    def _find_coding_languages_ratio(self):
        '''
        Calculates the ratio of all coding languages
        present in the `ProjectReports` used to
        create the `UserReport` for the
        `USER_CODING_LANGUAGE_RATIO` statistic.

        Simply aggregates the already-calculated project-level ratios.
        No need to re-filter files since that's already done at project level.
        '''
        lang_to_bytes = {}

        for proj_report in self.project_reports:
            # Get the already-calculated coding language ratio from the project
            proj_lang_ratio = proj_report.get_value(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value
            )

            if proj_lang_ratio is None:
                continue

            # Get the total byte count for this project to denormalize the ratios
            # We need actual byte counts to properly aggregate across projects
            proj_total_bytes = 0

            # Skip if project was created via from_statistics (no file_reports)
            if hasattr(proj_report, 'file_reports') and proj_report.file_reports is not None:
                for file_report in proj_report.file_reports:
                    file_size = file_report.get_value(
                        FileStatCollection.FILE_SIZE_BYTES.value)
                    if file_size is None:
                        file_size = file_report.get_value(
                            FileStatCollection.LINES_IN_FILE.value)
                    if file_size is None:
                        file_size = 1
                    proj_total_bytes += file_size

            # Convert ratios back to byte counts and aggregate
            for curr_lang, ratio in proj_lang_ratio.items():
                if curr_lang is None:
                    continue

                # Convert ratio back to bytes for this project
                lang_bytes = ratio * proj_total_bytes

                # Aggregate to user level
                if curr_lang in lang_to_bytes:
                    lang_to_bytes[curr_lang] += lang_bytes
                else:
                    lang_to_bytes[curr_lang] = lang_bytes

        if len(lang_to_bytes) < 1:
            return  # don't log this stat b/c there are no coding languages

        # Normalize to ensure ratios sum to 1.0 (100%)
        total_bytes = sum(lang_to_bytes.values())
        lang_ratio = {}

        if total_bytes > 0:
            for lang, byte_count in lang_to_bytes.items():
                # Round to 4 decimal places (0.01% precision)
                lang_ratio[lang] = round(byte_count / total_bytes, 4)

        self.user_stats.add(
            Statistic(UserStatCollection.USER_CODING_LANGUAGE_RATIO.value, lang_ratio))

    def generate_resume(self, email: Optional[str]) -> Resume:
        """
        Generates a Resume object based on the ResumeItem
        that are generated from the ProjectReports. As well
        as adding skills from the User Statistics.
        """

        weighted_skills = self.statistics.get_value(
            UserStatCollection.USER_SKILLS.value)

        resume = Resume(email, weighted_skills)

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
        from src.database.db import get_engine, UserReportTable

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
        from src.database.db import get_engine, UserReportTable

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
        from src.database.db import get_engine, UserReportTable

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

    @classmethod
    def from_statistics(cls, statistics: StatisticIndex) -> "UserReport":
        inst = cls.__new__(cls)
        BaseReport.__init__(inst, statistics)
        return inst

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
                        lang_name = lang.value[0]
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

        return "\n".join(lines)

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

    def get_chronological_skills(
        self,
        as_string: bool = True,
        newest_first: bool = False,
    ) -> list[str] | str:
        """
        Produce a chronological list of skills exercised by the user across all projects.

        Skills are inferred from PROJECT_SKILLS_DEMONSTRATED on each ProjectReport
        (i.e., the WeightedSkills list), and ordered by the earliest project start
        date in which they appear.

        If as_string is True, returns a newline-separated string of formatted lines:
            "Python — First exercised Jan 12, 2023"

        If as_string is False, returns a list of formatted strings in the same order.
        """
        if not getattr(self, "project_reports", None):
            return "" if as_string else []

        # Map skill_name -> earliest datetime it appears in any project
        skill_first_seen: dict[str, datetime | None] = {}

        for pr in self.project_reports:
            start_dt = self._coerce_datetime(
                pr.get_value(ProjectStatCollection.PROJECT_START_DATE.value)
            )
            skills = pr.get_value(
                ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value
            )

            if not skills:
                continue

            for ws in skills:
                name = getattr(ws, "skill_name", None) or str(ws)
                if not name:
                    continue

                current_first = skill_first_seen.get(name)

                if start_dt is None:
                    if current_first is None:
                        skill_first_seen[name] = None
                    continue

                if current_first is None or start_dt < current_first:
                    skill_first_seen[name] = start_dt

        if not skill_first_seen:
            return "" if as_string else []

        dated: list[tuple[str, datetime]] = []
        undated: list[str] = []

        for name, dt in skill_first_seen.items():
            if dt is not None:
                dated.append((name, dt))
            else:
                undated.append(name)

        # Sort dated skills by first_seen (oldest -> newest)
        dated.sort(key=lambda item: item[1])
        if newest_first:
            dated.reverse()

        lines: list[str] = []

        for name, dt in dated:
            formatted_date = self._fmt_mdy_short(dt)
            lines.append(f"{name} — First exercised {formatted_date}")

        # Skills with unknown first date go at the end
        for name in sorted(undated):
            lines.append(f"{name} — First exercised on an unknown date")

        if as_string:
            return "\n".join(lines)

        return lines
