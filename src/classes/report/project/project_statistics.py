"""
This file contains the logic for generating project statistics.
it utilizes the StatisticBuilder and StatisticCalculator classes
to create and compute various statistics related to projects.
"""

from typing import List
import os
from src.classes.statistic import Statistic, FileStatCollection, ProjectStatCollection, WeightedSkills
from src.classes.report import ProjectReport
from src.classes.report.statistic_builder import StatisticCalculation, StatisticReportBuilder
from src.classes.skills import SkillMapper
from datetime import datetime, timedelta, MINYEAR
from src.utils.data_processing import normalize
from typing import Optional


class ProjectStatisticCalculation(StatisticCalculation[ProjectReport]):
    """Base for project-scoped statistic calculations."""
    pass


class ProjectDates(ProjectStatisticCalculation):
    """
    Calculates a project's start and end date based on
    the file reports available. Logs statistics to
    `self.project_statistics`.
    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        # Set the value to 1 day in the future
        latest_date = datetime.now() + timedelta(days=1)
        earliest_date = datetime(MINYEAR, 1, 1, 0, 0, 0, 0)

        start_date = latest_date
        end_date = earliest_date

        for file_report in report.file_reports:
            curr_start_date = file_report.get_value(
                FileStatCollection.DATE_CREATED.value)
            curr_end_date = file_report.get_value(
                FileStatCollection.DATE_MODIFIED.value)

            # curr_start_date and curr_end_date are always datetime; if not, let comparison throw an error

            if curr_start_date and curr_start_date < start_date:
                start_date = curr_start_date

            if curr_end_date and curr_end_date > end_date:
                end_date = curr_end_date

        to_return = []

        if end_date != earliest_date:
            project_end_stat = Statistic(
                ProjectStatCollection.PROJECT_END_DATE.value, end_date)
            to_return.append(project_end_stat)

        if start_date != latest_date:
            project_start_stat = Statistic(
                ProjectStatCollection.PROJECT_START_DATE.value, start_date)
            to_return.append(project_start_stat)

        return to_return


class CodingLanguageRatio(ProjectStatisticCalculation):
    """
    Creates the project-level statistic of
    `CODING_LANGUAGE_RATIO`.
    Uses file-level statistics for byte counts.

    Note: File filtering (venv, config files, etc.) is handled by project_discovery.py
    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        langauges_to_bytes = {}

        # Track files by (filename, file_size) to detect true duplicates
        seen_file_signatures = {}

        # Sort file_reports to prioritize non-database paths
        sorted_reports = sorted(
            report.file_reports,
            key=lambda r: (
                'database' in str(r.filepath).lower(),
                str(r.filepath)
            )
        )

        # Map coding language to file sizes in bytes
        for file_report in sorted_reports:
            coding_language = file_report.get_value(
                FileStatCollection.CODING_LANGUAGE.value)

            if coding_language is None:
                continue

            # Use file-level statistics instead of os.path.getsize
            file_size = file_report.get_value(
                FileStatCollection.FILE_SIZE_BYTES.value)
            if file_size is None:
                # Fallback to line count if bytes not available
                file_size = file_report.get_value(
                    FileStatCollection.LINES_IN_FILE.value)
            if file_size is None:
                # Last resort: count as 1 byte
                file_size = 1

            # Create a signature to detect true duplicates
            # Only skip if BOTH filename AND size match (likely a database export duplicate)
            filepath_lower = str(file_report.filepath).lower()
            path_parts = filepath_lower.replace('\\', '/').split('/')
            filename = path_parts[-1] if path_parts else ''
            file_signature = (filename, file_size)

            if file_signature in seen_file_signatures:
                # This is likely a duplicate database export - skip it
                continue

            # Mark this file signature as seen
            seen_file_signatures[file_signature] = file_report.filepath

            if file_size > 0:
                langauges_to_bytes[coding_language] = langauges_to_bytes.get(
                    coding_language, 0) + file_size
            else:
                # Count empty files as 1 byte (test files are often empty)
                langauges_to_bytes[coding_language] = langauges_to_bytes.get(
                    coding_language, 0) + 1

        if len(langauges_to_bytes) == 0:
            return []

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

        return [Statistic(ProjectStatCollection.CODING_LANGUAGE_RATIO.value, lang_ratio)]


class ProjectWeightedSkills(ProjectStatisticCalculation):
    """
    Computes two project-level statistics:

    1. `PROJECT_SKILLS_DEMONSTRATED`
    - High-level skills inferred from file paths & imported packages
    - Deduped so each file contributes at most once per skill

    2. `PROJECT_FRAMEWORKS`
    - Raw counts of third-party frameworks/libraries (import frequency)
    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:

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

        dirnames = report._get_sub_dirs()

        # High-level skill tracking (deduped per file)
        high_level_skill_counter: dict[str, int] = {}
        high_level_skill_files: dict[str, set] = {}

        project_framework_counter: dict[str, int] = {}
        project_framework_files: dict[str, set] = {}

        for file_report in report.file_reports:
            imported_packages: Optional[list[str]] = file_report.get_value(
                FileStatCollection.IMPORTED_PACKAGES.value
            )

            # 1. Skill from filename (e.g., Dockerfile → DevOps)
            file_skill = SkillMapper.map_filepath_to_skill(
                file_report.filepath)
            if file_skill:
                count_one_per_file(
                    high_level_skill_counter,
                    high_level_skill_files,
                    file_skill.value,
                    file_report.filepath
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
                    file_report.filepath
                )

                package_skill = SkillMapper.map_package_to_skill(package)
                if package_skill:
                    count_one_per_file(
                        high_level_skill_counter,
                        high_level_skill_files,
                        package_skill.value,
                        file_report.filepath
                    )

        to_return = []

        def _add_weighted_stat(stat_key, counter: dict) -> None:
            """Adds a weighted `Statistic` entry if the counter has values."""
            if not counter:
                return

            total = sum(counter.values())
            weighted = [
                WeightedSkills(skill_name=k, weight=v / total)
                for k, v in counter.items()
            ]

            to_return.append(Statistic(stat_key, weighted))

        _add_weighted_stat(
            ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value,
            high_level_skill_counter
        )

        _add_weighted_stat(
            ProjectStatCollection.PROJECT_FRAMEWORKS.value,
            project_framework_counter
        )

        return to_return


class ProjectActivityTypeContributions(ProjectStatisticCalculation):
    """
    This function will analyze the user's
    contributions to each file domain in a
    project out of all of their contributions.

    If the user's email is configured, it will
    use `PERCENTAGE_LINES_COMMITTED` file stat.

    Otherwise, it is assumed that they worked on
    all files and we will just use the distrubition
    of the project files.
    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        activity_type_to_lines = {}
        git_analysis = True if report.email and report.project_repo else False

        for fr in report.file_reports:
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

        return [Statistic(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value, activity_type_to_lines)]


class ProjectAnalyzeGitAuthorship(ProjectStatisticCalculation):
    """
    Analyzes Git commit history to determine authorship statistics.
    This function uses `self.email` to calculate the user's commit percentage.
    If `self.email` is not set, this function should not run as we don't have
    the consent of the user.

    Creates the following project level statistics:
    - `IS_GROUP_PROJECT`: Boolean indicating if multiple authors contributed
    - `TOTAL_AUTHORS`: Total number of unique authors
    - `AUTHORS_PER_FILE`: Dictionary mapping file paths to number of unique authors
    - `USER_COMMIT_PERCENTAGE`: Percentage of commits made by the user (if applicable)

    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        if not report.email or not report.project_repo:
            return []

        repo = report.project_repo

        # Check if repository has any commits
        try:
            commit_count_by_author = {}
            for commit in repo.iter_commits():
                author_email = commit.author.email
                commit_count_by_author[author_email] = commit_count_by_author.get(
                    author_email, 0) + 1
        except ValueError:
            # Empty repository with no commits
            return []

        all_authors = set([author for author in commit_count_by_author.keys(
        ) if not author.endswith('@users.noreply.github.com')])

        total_authors = len(all_authors)
        total_commits = sum(commit_count_by_author.values())

        # Calculate user's commit percentage if project has multiple authors
        user_commit_percentage = None
        if total_authors > 1 and report.email:
            user_commits = commit_count_by_author.get(
                report.email, 0)
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

        return stats


class ProjectTotalContributionPercentage(ProjectStatisticCalculation):
    """
    Calculates:
    - ProjectStatCollection.TOTAL_PROJECT_LINES
    - ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS
    """

    def _total_lines(self, report) -> int:
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

        total = 0

        if report.project_repo:
            tracked_files = report.project_repo.git.ls_files().split("\n")
            for f in tracked_files:
                try:
                    with open(os.path.join(report.project_path, f), "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                        count = len(content.split("\n"))
                        total += count
                except (FileNotFoundError, IsADirectoryError):
                    pass  # skip directories or removed files
        else:
            for fr in report.file_reports:
                val = fr.get_value(FileStatCollection.LINES_IN_FILE.value)
                if val is not None:
                    total += val

        return total

    def _total_contribution_percentage(self, report: ProjectReport, project_lines: float) -> float:
        """
        Iterate over fileReports to get total lines responsible over whole project
        """

        total_contribution_lines = 0.0

        for file in report.file_reports:
            file_commit_pct = file.get_value(
                FileStatCollection.PERCENTAGE_LINES_COMMITTED.value)
            if file_commit_pct is not None:
                total_contribution_lines += file_commit_pct / 100 * \
                    file.get_value(FileStatCollection.LINES_IN_FILE.value)

        if project_lines > 0:
            return round((total_contribution_lines / project_lines) * 100, 2)

        return 0.0

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        to_return = []

        total_lines = self._total_lines(report)

        to_return.append(Statistic(
            ProjectStatCollection.TOTAL_PROJECT_LINES.value,
            total_lines))

        if report.project_repo and report.email:
            total_contribution = self._total_contribution_percentage(
                report, total_lines)

            to_return.append(Statistic(
                ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value, total_contribution
            ))

        return to_return


class ProjectStatisticReportBuilder(StatisticReportBuilder[ProjectReport]):
    """Base builder for project reports."""

    def __init__(self) -> None:
        self.calculators: list[ProjectStatisticCalculation] = [
            ProjectDates(),
            CodingLanguageRatio(),
            ProjectWeightedSkills(),
            ProjectActivityTypeContributions(),
            ProjectAnalyzeGitAuthorship(),
            ProjectTotalContributionPercentage(),
        ]

    def build(self, report: ProjectReport) -> List[Statistic]:
        """
        Compile all the project level statistics together into one
        statistic list
        """

        stats: List[Statistic] = []

        for calc in self.calculators:

            new_stats = calc.calculate(report)

            if new_stats:
                report.project_statistics.extend(new_stats)
                stats.extend(new_stats)

        return stats
