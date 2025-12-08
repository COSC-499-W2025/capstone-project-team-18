"""
This file defines the ProjectReport class
"""

import os
from typing import Dict, Optional
from pathlib import Path
import os
from git import Repo
from datetime import datetime, date, timedelta, MINYEAR

from src.classes.report.base_report import BaseReport
from src.classes.report.file_report import FileReport
from src.classes.statistic import Statistic, StatisticIndex, ProjectStatCollection, FileStatCollection, WeightedSkills
from src.classes.resume.bullet_point_builder import BulletPointBuilder
from src.classes.resume.resume import ResumeItem
from src.utils.data_processing import normalize
from src.classes.skills import SkillMapper


class ProjectReport(BaseReport):
    """
    The ProjectReport class utilizes many FileReports to
    create many Project Statistics about a single project.

    For example, maybe we sum up all the lines of written
    in a FileReport to create a project level statistics
    of "total lines written."
    """

    bullet_builder = BulletPointBuilder()

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
        if start_date and end_date:
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

    def __init__(self,
                 file_reports: Optional[list[FileReport]] = None,
                 project_path: Optional[str] = None,
                 project_name: Optional[str] = None,
                 user_email: Optional[str] = None,
                 statistics: Optional[StatisticIndex] = None,
                 project_repo: Optional[Repo] = None
                 ):
        """
        Initialize ProjectReport with file reports and optional Git analysis from zip file.

        Args:
            file_reports: List of FileReport objects to aggregate statistics from
            project_path: Optional path to project for Git analysis
            project_name: Optional project name for Git analysis
            statistics: Optional StatisicIndex
            project_repo: Optional Repo object for Git analysis
            user_email: Optional user email for Git authorship analysis

        NOTE: `statistics` should only be included when the `get_project_from_project_name()`
        function is creating a ProjectReport object from an existing row in
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

        # Aggregate statistics from file reports
        self._determine_start_end_dates()
        self._find_coding_languages_ratio()
        self._weighted_skills()
        self._activity_type_contributions()

        if self.email:
            self._analyze_git_authorship()

        project_lines = self._get_project_lines()

        if self.project_repo and self.email:
            self._total_contribution_percentage(project_lines)

        # Initialize the base class with the project statistics
        super().__init__(self.project_statistics)

    def _total_contribution_percentage(self, project_lines: float) -> None:
        # Iterate over fileReports to get total lines responsible over whole project
        total_contribution_lines = 0.0

        for file in self.file_reports:
            file_commit_pct = file.get_value(
                FileStatCollection.PERCENTAGE_LINES_COMMITTED.value)
            if file_commit_pct is not None:
                total_contribution_lines += file_commit_pct / 100 * \
                    file.get_value(FileStatCollection.LINES_IN_FILE.value)
        if project_lines > 0:
            self.project_statistics.add(Statistic(
                ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value, round((total_contribution_lines / project_lines) * 100, 2)))
        else:
            self.project_statistics.add(Statistic(
                ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value, 0.0))

    def _get_project_lines(self) -> float:
        '''
        Calculate the total number of lines in a project.
        If the project is a git repo, iterate through every
        file in the repo and get the sum. Otherwise,
        compute the sum of all `LINES_IN_FILE` stats in a
        project's `self.file_reports[]`. Then, create a
        `TOTAL_PROJECT_LINES` statistic with the sum and
        return the value.

        :return float: Total number of lines in the project
        '''
        total = 0.0
        if self.project_repo:
            tracked_files = self.project_repo.git.ls_files().split("\n")
            for f in tracked_files:
                try:
                    with open(os.path.join(self.project_path, f), "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                        count = len(content.split("\n"))
                        total += count
                except (FileNotFoundError, IsADirectoryError):
                    pass  # skip directories or removed files
        else:
            for fr in self.file_reports:
                val = fr.get_value(FileStatCollection.LINES_IN_FILE.value)
                if val is not None:
                    total += val

        self.project_statistics.add(Statistic(
            ProjectStatCollection.TOTAL_PROJECT_LINES.value, total))
        return total

    def _activity_type_contributions(self) -> None:
        """
        This function will analyze the user's
        contributions to each file domain in a
        project out of all of their contributions.

        If the user's email is configured, it will
        use PERCENTAGE_LINES_COMMITTED file stat.

        Otherwise, it is assumed that they worked on
        all files and we will just use the distrubition
        of the project files.
        """

        activity_type_to_lines = {}
        git_analysis = True if self.email and self.project_repo else False

        for fr in self.file_reports:
            file_domain = fr.get_value(FileStatCollection.TYPE_OF_FILE.value)

            lines_in_file = fr.get_value(
                FileStatCollection.LINES_IN_FILE.value)

            if not file_domain or not lines_in_file:
                continue

            percent = 1

            # If git analysis, check to see if the user has contributed
            # if so, take that percent. Else, that file is local and assume
            # they contributed to it themeseleves
            if git_analysis:
                percent_lines_commited = fr.get_value(
                    FileStatCollection.PERCENTAGE_LINES_COMMITTED.value)

                if percent_lines_commited is not None:
                    percent = percent_lines_commited / 100

            prev_lines = activity_type_to_lines.get(file_domain, 0)

            activity_type_to_lines[file_domain] = prev_lines + \
                lines_in_file * percent

        normalize(activity_type_to_lines)

        self.project_statistics.add(Statistic(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value, activity_type_to_lines))

    def _get_sub_dirs(self) -> set[str]:
        """
        Get the sub directory of this project
        top level directory
        """

        root = Path(self.project_path)
        return {p.name for p in root.rglob('*') if p.is_dir()}

    def _weighted_skills(self) -> None:
        """
        Computes two project-level statistics:

        1. PROJECT_SKILLS_DEMONSTRATED
        - High-level skills inferred from file paths & imported packages
        - Deduped so each file contributes at most once per skill

        2. PROJECT_FRAMEWORKS
        - Raw counts of third-party frameworks/libraries (import frequency)
        """

        def count_one_per_file(counter: dict, fileset: dict, key: str, filepath: str):
            """
            Increments `counter[key]` only once per filepath.
            Ensures high-level skills are deduped per file.
            """
            if key not in fileset:
                fileset[key] = set()

            if filepath not in fileset[key]:
                fileset[key].add(filepath)
                counter[key] = counter.get(key, 0) + 1

        dirnames = self._get_sub_dirs()

        # High-level skill tracking (deduped per file)
        high_level_skill_counter: Dict[str, int] = {}
        high_level_skill_files: Dict[str, set] = {}

        project_framework_counter: Dict[str, int] = {}
        project_framework_files: Dict[str, set] = {}

        for report in self.file_reports:
            imported_packages: Optional[list[str]] = report.get_value(
                FileStatCollection.IMPORTED_PACKAGES.value
            )

            # 1. Skill from filename (e.g., Dockerfile → DevOps)
            file_skill = SkillMapper.map_filepath_to_skill(report.filepath)
            if file_skill:
                count_one_per_file(
                    high_level_skill_counter,
                    high_level_skill_files,
                    file_skill.value,
                    report.filepath
                )

            if imported_packages is None or imported_packages == []:
                continue

            for package in imported_packages:

                if package == "app" or package in dirnames:
                    continue

                count_one_per_file(
                    project_framework_counter,
                    project_framework_files,
                    package,
                    report.filepath
                )

                package_skill = SkillMapper.map_package_to_skill(package)
                if package_skill:
                    count_one_per_file(
                        high_level_skill_counter,
                        high_level_skill_files,
                        package_skill.value,
                        report.filepath
                    )

        def _add_weighted_stat(stat_key, counter: dict) -> None:
            """Adds a weighted Statistic entry if the counter has values."""
            if not counter:
                return

            total = sum(counter.values())
            weighted = [
                WeightedSkills(skill_name=k, weight=v / total)
                for k, v in counter.items()
            ]

            self.project_statistics.add(
                Statistic(stat_key, weighted)
            )

        _add_weighted_stat(
            ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
            high_level_skill_counter
        )

        _add_weighted_stat(
            ProjectStatCollection.PROJECT_FRAMEWORKS.value,
            project_framework_counter
        )

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

            # curr_start_date and curr_end_date are always datetime; if not, let comparison throw an error

            if curr_start_date and curr_start_date < start_date:
                start_date = curr_start_date

            if curr_end_date and curr_end_date > end_date:
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

    def _find_coding_languages_ratio(self) -> None:
        """
        Creates the project level statistic of
        CODING_LANGUAGE_RATIO.
        Uses file-level statistics for byte counts.

        Note: File filtering (venv, config files, etc.) is handled by project_discovery.py
        """
        langauges_to_bytes = {}

        # Track files by (filename, file_size) to detect true duplicates
        seen_file_signatures = {}

        # Sort file_reports to prioritize non-database paths
        sorted_reports = sorted(
            self.file_reports,
            key=lambda r: (
                'database' in str(r.filepath).lower(),
                str(r.filepath)
            )
        )

        # Map coding language to file sizes in bytes
        for report in sorted_reports:
            coding_language = report.get_value(
                FileStatCollection.CODING_LANGUAGE.value)

            if coding_language is None:
                continue

            # Use file-level statistics instead of os.path.getsize
            file_size = report.get_value(
                FileStatCollection.FILE_SIZE_BYTES.value)
            if file_size is None:
                # Fallback to line count if bytes not available
                file_size = report.get_value(
                    FileStatCollection.LINES_IN_FILE.value)
            if file_size is None:
                # Last resort: count as 1 byte
                file_size = 1

            # Create a signature to detect true duplicates
            # Only skip if BOTH filename AND size match (likely a database export duplicate)
            filepath_lower = str(report.filepath).lower()
            path_parts = filepath_lower.replace('\\', '/').split('/')
            filename = path_parts[-1] if path_parts else ''
            file_signature = (filename, file_size)

            if file_signature in seen_file_signatures:
                # This is likely a duplicate database export - skip it
                continue

            # Mark this file signature as seen
            seen_file_signatures[file_signature] = report.filepath

            if file_size > 0:
                langauges_to_bytes[coding_language] = langauges_to_bytes.get(
                    coding_language, 0) + file_size
            else:
                # Count empty files as 1 byte (test files are often empty)
                langauges_to_bytes[coding_language] = langauges_to_bytes.get(
                    coding_language, 0) + 1

        if len(langauges_to_bytes) == 0:
            return

        # Calculate the bytes as percentages of the total
        lang_ratio = {}
        for lang, byte_count in langauges_to_bytes.items():
            lang_ratio[lang] = byte_count

        # Normalize to ensure ratios sum to 1.0 (100%)
        total_ratio = sum(lang_ratio.values())
        if total_ratio > 0:
            for lang in lang_ratio:
                # Round to 4 decimal places (0.01% precision)
                lang_ratio[lang] = round(lang_ratio[lang] / total_ratio, 4)

        self.project_statistics.add(
            Statistic(ProjectStatCollection.CODING_LANGUAGE_RATIO.value, lang_ratio))

    @classmethod
    def from_statistics(cls, statistics: StatisticIndex) -> "ProjectReport":
        """Create a ProjectReport directly from a StatisticIndex for testing"""
        inst = cls.__new__(cls)
        BaseReport.__init__(inst, statistics)
        inst.project_name = "TESTING ONLY SHOULD SEE THIS IN PYTEST"
        inst.file_reports = []
        return inst

    def _analyze_git_authorship(self) -> None:
        """
        Analyzes Git commit history to determine authorship statistics.
        This function uses self.email to calculate the user's commit percentage.
        If self.email is not set, this function should not run as we don't have
        the consent of the user.

        Creates the following project level statistics:
        - IS_GROUP_PROJECT: Boolean indicating if multiple authors contributed
        - TOTAL_AUTHORS: Total number of unique authors
        - AUTHORS_PER_FILE: Dictionary mapping file paths to number of unique authors
        - USER_COMMIT_PERCENTAGE: Percentage of commits made by the user (if applicable)

        """

        if self.project_repo is None:
            return

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
        if total_authors > 1 and self.email:
            user_commits = commit_count_by_author.get(
                self.email, 0)
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
