"""
Reports hold statistics.
"""
from typing import Any, Optional
from pathlib import Path
import tempfile
import shutil
import zipfile
from git import Repo, InvalidGitRepositoryError
from .statistic import Statistic, StatisticTemplate, StatisticIndex, ProjectStatCollection, FileStatCollection, UserStatCollection, WeightedSkills, CodingLanguage
from git import NoSuchPathError, Repo, InvalidGitRepositoryError
from .resume import Resume, ResumeItem, bullet_point_builder
from typing import Any
from datetime import datetime, date, timedelta, MINYEAR


class BaseReport:
    """
    This is the BaseReport class. A report is a class that holds
    statistics.
    """

    def __init__(self, statistics: StatisticIndex):
        self.statistics = statistics

    def add_statistic(self, stat: Statistic):
        self.statistics.add(stat)

    def get(self, template: StatisticTemplate):
        return self.statistics.get(template)

    def get_value(self, template: StatisticTemplate) -> Any:
        """
        Retrieves the value of a Statistic from the index by its template.
        Returns None if not found.
        """
        return self.statistics.get_value(template)

    def to_dict(self) -> dict[str, Any]:
        return self.statistics.to_dict()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.to_dict()}>"


class FileReport(BaseReport):
    """
    The FileReport class is the lowest level report. It is made
    by file-type specific, analyzers.
    """

    filepath: str

    def __init__(self, statistics: StatisticIndex, filepath: str):
        super().__init__(statistics)
        self.filepath = filepath

    @classmethod
    def create_with_analysis(cls, filepath: str) -> "FileReport":
        """
        Create a FileReport with automatic file type detection and analysis.
        This includes:
                - Natural Language statistics for appropriate langauge based files
                - Python statistics for appropriate Python files
                - Java statistics for appropriate Java files
                - JavaScript statistics for appropriate JavaScript files
                - Text-based statistics for appropriate text based files (i.e. css, html, xml, json, yml, yaml)
        """
        from .analyzer import get_appropriate_analyzer
        analyzer = get_appropriate_analyzer(filepath)
        return analyzer.analyze()

    def get_filename(self):
        return Path(self.filepath).name


class ProjectReport(BaseReport):
    """
    The ProjectReport class utilizes many FileReports to
    create many Project Statistics about a single project.

    For example, maybe we sum up all the lines of written
    in a FileReport to create a project level statistics
    of "total lines written."
    """

    def __init__(self,
                 file_reports: Optional[list[FileReport]] = None,
                 project_path: Optional[str] = None,
                 project_name: Optional[str] = None,
                 user_email: Optional[str] = None,
                 statistics: Optional[StatisticIndex] = None,
                 project_repo: Optional[Repo] = None,
                 ):
        """
        Initialize ProjectReport with file reports and optional Git analysis from zip file.

        Args:
            file_reports: List of FileReport objects to aggregate statistics from
            project_path: Optional path to project for Git analysis
            project_name: Optional project name for Git analysis
            statistics: Optional StatisicIndex
            project_repo: Optional Repo object for Git analysis
        """

            NOTE: `statistics` should only be included when the `get_project_from_project_name()`
            function is creating a ProjectReport object from an existing row in
            the `project_report` table!
        """
        self.file_reports = file_reports or []
        self.project_name = project_name or "Unknown Project"

        if statistics is None:
            self.project_statistics = StatisticIndex()
            self.project_repo = project_repo
            # Aggregate statistics from file reports
            self._determine_start_end_dates()
            self._find_coding_languages_ratio()
            self._calculate_ari_score()
            self._weighted_skills()
            self._analyze_git_authorship(user_email)

            # Add Git analysis statistics if zip file is provided
            if project_path and project_name:
                git_stats = self._analyze_git_authorship(
                    project_path, project_name, user_email)
                if git_stats:
                    for stat in git_stats:
                        self.project_statistics.add(stat)
        else:
            self.project_statistics = statistics


        # Initialize the base class with the project statistics
        super().__init__(self.project_statistics)

    def _weighted_skills(self) -> None:
        """
        Creates the project level statistic of
        WEIGHTED_SKILLS.

        We do this by analyzing the
        imported packages in coding files.

        We weight the skills based on how many
        files import the package.
        """

        skill_to_count = {}

        # Map coding language to lines of code
        for report in self.file_reports:

            imported_packages: Optional[list[str]] = report.get_value(
                FileStatCollection.IMPORTED_PACKAGES.value)

            if imported_packages is None:
                continue

            for package in imported_packages:
                skill_to_count[package] = skill_to_count.get(package, 0) + 1

        if len(skill_to_count) == 0:
            # Don't log this stat if it isn't a coding project
            return

        total = sum(skill_to_count.values())
        weighted_skills = [
            WeightedSkills(skill_name=k, weight=v / total)
            for k, v in skill_to_count.items()
        ]

        self.project_statistics.add(
            Statistic(ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value, weighted_skills))

    def _determine_start_end_dates(self) -> None:
        """
        Calculates a project start and end date based on
        the file reports available. Logs statistics to
        self.project_statistics.

        Note here. Currently when we unzip with Linux's
        "unzip" utility, it sets the date created to the
        current date, not the date in the zip file. The
        dates we need to analyze are the date modified
        and the date accessed.
        """

        # Set the value to 1 day in the future
        latest_date = datetime.now() + timedelta(days=1)
        earliest_date = datetime(MINYEAR, 1, 1, 0, 0, 0, 0)

        start_date = latest_date
        end_date = earliest_date

        for report in self.file_reports:
            curr_start_date = report.get_value(
                FileStatCollection.DATE_CREATED.value)
            curr_end_date = report.get_value(
                FileStatCollection.DATE_MODIFIED.value)

            # Coerce date to datetime for safe comparisons
            if isinstance(curr_start_date, date) and not isinstance(curr_start_date, datetime):
                curr_start_date = datetime(
                    curr_start_date.year, curr_start_date.month, curr_start_date.day
                )
            if isinstance(curr_end_date, date) and not isinstance(curr_end_date, datetime):
                curr_end_date = datetime(
                    curr_end_date.year, curr_end_date.month, curr_end_date.day
                )

            if curr_start_date is not None and curr_start_date < start_date:
                start_date = curr_start_date

            if curr_end_date is not None and curr_end_date > end_date:
                end_date = curr_end_date

        if end_date != earliest_date:
            project_end_stat = Statistic(
                ProjectStatCollection.PROJECT_END_DATE.value, end_date)
            self.project_statistics.add(project_end_stat)

        if start_date != latest_date:
            project_start_stat = Statistic(
                ProjectStatCollection.PROJECT_START_DATE.value, start_date)
            self.project_statistics.add(project_start_stat)

    def generate_resume_item(self) -> ResumeItem:
        """
        Generates a ResumeItem from the project report statistics.

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

        bullet_points = bullet_point_builder(self)

        return ResumeItem(
            title=self.project_name,
            bullet_points=bullet_points,
            start_date=start_date,
            end_date=end_date
        )

    def _find_coding_languages_ratio(self) -> None:
        """
        Creates the project level statistic of
        CODING_LANGUAGE_RATIO.
        """

        langauges_to_loc = {}

        # Map coding language to lines of code
        for report in self.file_reports:

            coding_language = report.get_value(
                FileStatCollection.CODING_LANGUAGE.value)

            if coding_language is None:
                continue

            loc = report.get_value(FileStatCollection.LINES_IN_FILE.value)

            langauges_to_loc[coding_language] = loc + \
                langauges_to_loc.get(coding_language, 0)

        if len(langauges_to_loc) == 0:
            # Don't log this stat if it isn't a coding project
            return

        # Calcuate the loc as percentages of the total
        total = sum(langauges_to_loc.values())
        language_ratio = {k: (v / total) for k,
                          v in langauges_to_loc.items()}

        self.project_statistics.add(
            Statistic(ProjectStatCollection.CODING_LANGUAGE_RATIO.value, language_ratio))

    def _calculate_ari_score(self):
        '''
        Uses all of the FileReports that make up the ProjectReport
        to calculate the average ARI writing score for the project
        using all files that have the `ARI_WRITING_SCORE` stat.
        '''
        avg_score = 0
        scores_count = 0  # the number of FileReports that have an ARI stat
        for report in self.file_reports:
            curr_score = report.get_value(
                FileStatCollection.ARI_WRITING_SCORE.value)
            if curr_score is None:
                continue
            scores_count += 1
            avg_score += curr_score
        if scores_count > 0:
            avg_score /= scores_count
        self.project_statistics.add(
            Statistic(ProjectStatCollection.AVG_ARI_WRITING_SCORE.value, float(avg_score)))

    @classmethod
    def from_statistics(cls, statistics: StatisticIndex) -> "ProjectReport":
        """Create a ProjectReport directly from a StatisticIndex for testing"""
        inst = cls.__new__(cls)
        BaseReport.__init__(inst, statistics)
        inst.project_name = "TESTING ONLY SHOULD SEE THIS IN PYTEST"
        return inst

    def _analyze_git_authorship(self, user_email: Optional[str] = None) -> None:
        """
        Analyzes Git commit history to determine authorship statistics.

        Creates the following project level statistics:
        - IS_GROUP_PROJECT: Boolean indicating if multiple authors contributed
        - TOTAL_AUTHORS: Total number of unique authors
        - AUTHORS_PER_FILE: Dictionary mapping file paths to number of unique authors
        - USER_COMMIT_PERCENTAGE: Percentage of commits made by the user (if applicable)

        Args:
            user_email: Optional email of the user to calculate their commit percentage
        """

        if self.project_repo is None:
            return None

        repo = self.project_repo

        # Check if repository has any commits
        try:
            commit_count_by_author = {}
            for commit in repo.iter_commits():
                author_email = commit.author.email
                commit_count_by_author[author_email] = commit_count_by_author.get(
                    author_email, 0) + 1
        except ValueError:
            # Empty repository with no commits
            return None

        all_authors = set([author for author in commit_count_by_author.keys(
        ) if not author.endswith('@users.noreply.github.com')])

        total_authors = len(all_authors)
        total_commits = sum(commit_count_by_author.values())

        # Calculate user's commit percentage if project has multiple authors
        user_commit_percentage = None
        if total_authors > 1 and user_email:
            user_commits = commit_count_by_author.get(
                user_email, 0)
            if total_commits > 0:
                user_commit_percentage = (
                    user_commits / total_commits) * 100

        authors_per_file = {}
        for item in repo.tree().traverse():
            if item.type == 'blob':
                try:
                    file_authors = {
                        c.author.email for c in repo.iter_commits(paths=item.path)}
                    authors_per_file[item.path] = len(file_authors)
                except Exception:
                    continue

        stats = [
            Statistic(
                ProjectStatCollection.IS_GROUP_PROJECT.value, total_authors > 1),
            Statistic(
                ProjectStatCollection.TOTAL_AUTHORS.value, total_authors),
            Statistic(
                ProjectStatCollection.AUTHORS_PER_FILE.value, authors_per_file)
        ]

        # Add user commit percentage if applicable
        if user_commit_percentage is not None:
            stats.append(
                Statistic(
                    ProjectStatCollection.USER_COMMIT_PERCENTAGE.value,
                    round(user_commit_percentage, 2)
                )
            )

        self.project_statistics.extend(stats)


class UserReport(BaseReport):
    """
    This UserReport class hold Statistics about the user. It is made
    from many different ReportReports
    """

    def __init__(self, project_reports: list[ProjectReport]):
        """
        Initialize UserReport with project reports to calculate user-level statistics.

        This method calculates user-level statistics by finding:
        - User start date: earliest project start date across all projects
        - User end date: latest project end date across all projects

        Args:
            project_reports: List of ProjectReport objects containing project-level statistics
        """

        self.resume_items = [project_reports.generate_resume_item()
                             for project_reports in project_reports]
        self.project_reports = project_reports or []

        # Build list of user-level statistics
        self.user_stats = StatisticIndex()

        # Function calls to generate statistics
        self._determine_start_end_dates()
        self._find_coding_languages_ratio()
        self._calculate_user_ari()

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
        '''
        lang_ratio = {}

        for proj_report in self.project_reports:
            proj_lang_ratio = proj_report.get_value(
                ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

            if proj_lang_ratio is None:
                continue

            for curr_lang, ratio in proj_lang_ratio.items():
                if curr_lang is None:
                    continue

                if curr_lang in lang_ratio:
                    # language & ratio have already been added from another report
                    lang_ratio[curr_lang] += ratio
                else:
                    # add new language & ratio
                    lang_ratio[curr_lang] = ratio

        if len(lang_ratio) < 1:
            return  # don't log this stat b/c there are no coding languages

        # now, we need to compute the even division the ratio of each language between all projects
        for lang, ratio in lang_ratio.items():
            ratio /= len(lang_ratio)
            lang_ratio[lang] = ratio

        self.user_stats.add(
            Statistic(UserStatCollection.USER_CODING_LANGUAGE_RATIO.value, lang_ratio))

    def _calculate_user_ari(self):
        '''
        Uses all of the ProjectReports that make up the UserReport
        to calculate the average ARI writing score for the user
        '''
        avg_score = 0
        scores_count = 0  # the number of FileReports that have an ARI stat
        for report in self.project_reports:
            curr_score = report.get_value(
                ProjectStatCollection.AVG_ARI_WRITING_SCORE.value)
            if curr_score is None:
                continue
            scores_count += 1
            avg_score += curr_score
        if scores_count > 0:
            avg_score /= scores_count
        self.user_stats.add(
            Statistic(UserStatCollection.USER_ARI_WRITING_SCORE.value, float(avg_score)))

    def generate_resume(self) -> Resume:
        """
        Generates a Resume object based on the ResumeItem
        that are generated from the ProjectReports. As well
        as adding skills from the User Statistics.
        """

        resume = Resume()

        for item in self.resume_items:
            resume.add_item(item)

        return resume

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
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime(val.year, val.month, val.day)
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val)
            except Exception:
                return None
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%fZ"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    pass
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                return None
        return None

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
                            return f"{n} ({w})" if w is not None else f"{n}"
                        skills_line = ", ".join(_skill_str(ws) for ws in value)
                except Exception:
                    pass
                lines.append(f"Your skills include: {skills_line}.")
                continue

            title = self._title_from_name(name)

            if name == UserStatCollection.USER_ARI_WRITING_SCORE.value.name:
                score = 0
                score += self.get_value(
                    UserStatCollection.USER_ARI_WRITING_SCORE.value)
                skills_line = f"Your Automated readability index (ARI) score: {score}"

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
                        percent = f"{int(ratio * 100)}%"
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

        return "\n".join(lines)
