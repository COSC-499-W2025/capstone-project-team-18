"""
User-level statistic calculation classes and a report builder.

Mirrors the structure used for project statistics.
"""
from typing import List, TYPE_CHECKING, Optional, Type
from datetime import datetime

from src.core.report.statistic_builder import StatisticCalculation, StatisticReportBuilder
from src.core.statistic import Statistic, UserStatCollection, WeightedSkills, FileStatCollection, ProjectStatCollection

if TYPE_CHECKING:
    # Import for type checking only to avoid circular imports at runtime
    from src.core.report import UserReport


class UserStatisticCalculation(StatisticCalculation["UserReport"]):
    """Base for user-scoped statistic calculations."""
    pass


class UserDates(UserStatisticCalculation):
    """
    Calculate earliest user start and latest user end across projects.
    """

    def calculate(self, report: "UserReport") -> List[Statistic]:
        # Loop through and find the earliest start date and latest end date of all projects
        latest_date = datetime.max
        earliest_date = datetime.min

        # For checking that the time range is valid
        start_date = latest_date
        end_date = earliest_date

        for pr in report.project_reports:
            curr_start_date = pr.get_value(
                ProjectStatCollection.PROJECT_START_DATE.value)
            curr_end_date = pr.get_value(
                ProjectStatCollection.PROJECT_END_DATE.value)

            if curr_start_date is not None and curr_start_date < start_date:
                start_date = curr_start_date
            if curr_end_date is not None and curr_end_date > end_date:
                end_date = curr_end_date

        to_return: List[Statistic] = []

        # Make sure that the values were actually updated
        if start_date != latest_date:
            to_return.append(
                Statistic(UserStatCollection.USER_START_DATE.value, start_date))

        if end_date != earliest_date:
            to_return.append(
                Statistic(UserStatCollection.USER_END_DATE.value, end_date))

        return to_return


class UserCodingLanguageRatio(UserStatisticCalculation):
    """
    Calculates the ratio of all coding languages
    present in the `ProjectReports` used to
    create the `UserReport` for the
    `USER_CODING_LANGUAGE_RATIO` statistic.

    Simply aggregates the already-calculated project-level ratios.
    No need to re-filter files since that's already done at project level.
    """

    def calculate(self, report: "UserReport") -> List[Statistic]:
        lang_to_bytes = {}

        for proj_report in report.project_reports:

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
            return []

        total_bytes = sum(lang_to_bytes.values())
        lang_ratio = {}

        if total_bytes > 0:
            for lang, byte_count in lang_to_bytes.items():
                # Round to 4 decimal places (0.01% precision)
                lang_ratio[lang] = round(byte_count / total_bytes, 4)

        return [Statistic(UserStatCollection.USER_CODING_LANGUAGE_RATIO.value, lang_ratio)]


class UserWeightedSkills(UserStatisticCalculation):
    """
    Calculates the user level stat of USER_SKILLS.

    We do this by lopping through a project level skills.
    The weight of a user skill, is the project level weight
    multiplied by the projects weight score.
    """

    def calculate(self, report: "UserReport") -> List[Statistic]:
        users_skills = {}

        for project in report.project_reports:
            project_weighted_skills = project.statistics.get_value(
                ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value
            )

            if project_weighted_skills is None:
                continue

            for weighted_skill in project_weighted_skills:
                # If already a user skill, get weight
                prev_weight = users_skills.get(weighted_skill.skill_name, 0)

                # Add the weight and skill name to user_skills
                users_skills[weighted_skill.skill_name] = prev_weight + \
                    weighted_skill.weight * project.get_project_weight()

        user_weighted_skills = [WeightedSkills(
            skill_name=k, weight=v) for k, v in users_skills.items()]

        # Always return a statistic for USER_SKILLS (may be empty list)
        return [Statistic(UserStatCollection.USER_SKILLS.value, user_weighted_skills)]


class UserCommitActivityTimeline(UserStatisticCalculation):
    """
    Calculates the timeline of each commit, to use in a contribution graph.

    Maps through commit history and also gets average
    commits for the group to utilize in
    an alternative contribution graph view.
    """

    def calculate(self, report: "UserReport") -> List[Statistic]:
        commits_dict = {}
        user_commits_dict = {}

        for project_report in report.project_reports:
            if project_report.project_repo is None:
                continue

            for commit in project_report.project_repo.iter_commits():
                date = datetime.fromtimestamp(
                    commit.authored_date).strftime("%Y-%m-%d")
                commits_dict[date] = commits_dict.get(date, 0) + 1

                if commit.author.email == project_report.email or (project_report.github and project_report.github in commit.author.email):
                    user_commits_dict[date] = user_commits_dict.get(
                        date, 0) + 1

        return [Statistic(UserStatCollection.COMMIT_ACTIVITY_TIMELINE.value, {2024-12-7: 3, 2024-12-8: 5}), Statistic(UserStatCollection.TOTAL_COMMIT_ACTIVITY_TIMELINE.value, {2024-12-7: 2, 2024-12-8: 10})]

        return [Statistic(UserStatCollection.COMMIT_ACTIVITY_TIMELINE.value, dict(sorted(user_commits_dict.items()))), Statistic(UserStatCollection.TOTAL_COMMIT_ACTIVITY_TIMELINE.value, dict(sorted(commits_dict.items())))]


class UserStatisticReportBuilder(StatisticReportBuilder["UserReport"]):
    ALL_CALCULATORS = [
        UserDates,
        UserCodingLanguageRatio,
        UserWeightedSkills,
        UserCommitActivityTimeline,
    ]

    def __init__(self, calculator_classes: Optional[list[Type]] = None) -> None:
        super().__init__(self.ALL_CALCULATORS, calculator_classes)
