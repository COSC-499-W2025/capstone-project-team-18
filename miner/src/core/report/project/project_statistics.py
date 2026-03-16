"""
This file contains the logic for generating project statistics.
it utilizes the StatisticBuilder and StatisticCalculation classes
to create and compute various statistics related to projects.
"""

from typing import List, Type
import os
import json
import re
from pathlib import Path
from src.core.statistic import Statistic, FileStatCollection, ProjectStatCollection, WeightedSkills
from src.core.report import ProjectReport
from src.core.report.statistic_builder import StatisticCalculation, StatisticReportBuilder
from src.core.ML.models.azure_foundry_manager import AzureFoundryManager, azure_openai_enabled
from src.core.statistic.skills import SkillMapper
from datetime import datetime, timedelta, MINYEAR
from src.utils.data_processing import normalize
from src.infrastructure.log.logging import get_logger
from src.core.ML.models.readme_analysis import readme_insights
from src.core.ML.models.contribution_analysis.commit_classifier import ContributionPatternOutput, CONTRIBUTION_PATTERN_PROMPT
from src.core.project_discovery.ignore_constants import *
from typing import Optional

logger = get_logger(__name__)


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

        non_user_authors_by_file: dict[str, int] = {}
        if report.project_repo and report.email:
            try:
                non_user_authors_by_file = self._get_nonUser_authors_per_file(
                    report.project_repo,
                    report.email,
                )
            except Exception:
                non_user_authors_by_file = {}

        # High-level skill tracking (deduped per file)
        high_level_skill_counter: dict[str, int] = {}
        high_level_skill_files: dict[str, set] = {}

        group_high_level_skill_counter: dict[str, int] = {}
        group_high_level_skill_files: dict[str, set] = {}

        project_framework_counter: dict[str, int] = {}
        project_framework_files: dict[str, set] = {}

        group_project_framework_counter: dict[str, int] = {}
        group_project_framework_files: dict[str, set] = {}

        # Tracks all skills (high-level + package-mapped) that each filepath demonstrates.
        # Used later to build the commit-date timeline for PROJECT_SKILL_ACTIVITY.
        file_to_skills: dict[str, set[str]] = {}

        for file_report in report.file_reports:
            imported_packages: Optional[list[str]] = file_report.get_value(
                FileStatCollection.IMPORTED_PACKAGES.value
            )

            # 1. Skill from filename (e.g., Dockerfile → DevOps)
            file_skill = SkillMapper.map_filepath_to_skill(
                file_report.filepath)
            is_group_file = True if non_user_authors_by_file.get(
                file_report.filepath, 0) >= 1 else False
            if file_skill:
                count_one_per_file(
                    high_level_skill_counter,
                    high_level_skill_files,
                    file_skill.value,
                    file_report.filepath
                )
                if is_group_file:
                    count_one_per_file(
                        group_high_level_skill_counter,
                        group_high_level_skill_files,
                        file_skill.value,
                        file_report.filepath
                    )
                # Record skill → filepath mapping for activity timeline
                file_to_skills.setdefault(
                    file_report.filepath, set()).add(file_skill.value)

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
                if is_group_file:
                    count_one_per_file(
                        group_project_framework_counter,
                        group_project_framework_files,
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
                    if is_group_file:
                        count_one_per_file(
                            group_high_level_skill_counter,
                            group_high_level_skill_files,
                            package_skill.value,
                            file_report.filepath
                        )
                    file_to_skills.setdefault(
                        file_report.filepath, set()).add(package_skill.value)

        skill_activity: dict[str, list[str]] = {}
        if report.project_repo and file_to_skills:
            try:
                for filepath, skills in file_to_skills.items():
                    file_commits = list(
                        report.project_repo.iter_commits(paths=filepath)
                    )
                    for commit in file_commits:
                        date_str = commit.committed_datetime.strftime(
                            "%Y-%m-%d")
                        for skill in skills:
                            skill_activity.setdefault(
                                skill, []).append(date_str)
            except Exception:
                skill_activity = {}

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

        _add_weighted_stat(
            ProjectStatCollection.GROUP_PROJECT_SKILLS_DEMONSTRATED.value,
            group_high_level_skill_counter
        )

        _add_weighted_stat(
            ProjectStatCollection.GROUP_PROJECT_FRAMEWORKS.value,
            group_project_framework_counter
        )

        to_return.append(Statistic(
            ProjectStatCollection.PROJECT_SKILL_ACTIVITY.value,
            skill_activity,
        ))

        return to_return

    def _get_nonUser_authors_per_file(self, repo, email) -> dict[str, int]:
        """We want to increment certain statistics if they are contributed to by authors other than the user"""
        authors_per_file: dict[str, set[str]] = {}

        for commit in repo.iter_commits():
            if not hasattr(commit, "author") or not hasattr(commit.author, "email"):
                continue

            author_email = commit.author.email
            if author_email == email:
                continue

            # Get files changed in this commit
            if commit.parents:
                diffs = commit.parents[0].diff(commit)
                for diff in diffs:
                    # Use b_path for new/modified files
                    file_path = diff.b_path if diff.b_path else diff.a_path
                    if file_path:
                        if file_path not in authors_per_file:
                            authors_per_file[file_path] = set()
                        authors_per_file[file_path].add(author_email)
            else:
                # First commit, all files are new
                for item in commit.tree.traverse():
                    if item.type == "blob":  # It's a file
                        if item.path not in authors_per_file:
                            authors_per_file[item.path] = set()
                        authors_per_file[item.path].add(author_email)

        # Convert sets to counts
        return {path: len(authors) for path, authors in authors_per_file.items()}


class ProjectReadmeInsights(ProjectStatisticCalculation):
    """
    Aggregates README key phrases, themes, and tone into project-level stats.
    """

    def _pick_majority(self, counts: dict[str, int]) -> str | None:
        if not counts:
            return None
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[0][0]

    def _infer_tags_from_paths(self, file_reports) -> list[str]:
        """
        Infer feature/domain tags when README signals are missing.
        """
        inferred: list[str] = []
        seen: set[str] = set()

        def _push(tag: str):
            label = str(tag or "").strip()
            if not label:
                return
            key = label.lower()
            if key in seen:
                return
            seen.add(key)
            inferred.append(label)

        low_signal = {
            "base", "main", "app", "application", "activity", "fragment",
            "screen", "view", "utils", "helper", "model", "service",
        }

        for fr in file_reports:
            path_text = str(getattr(fr, "filepath", "") or "")
            lowered = path_text.lower()
            name = Path(path_text).name

            if "androidmanifest.xml" in lowered:
                _push("Android Application")
            if "trip" in lowered:
                _push("Trip Creation")
            if "itinerary" in lowered:
                _push("Itinerary")
            if "event" in lowered:
                _push("Event Search")
            if "admin" in lowered:
                _push("Admin Panel")
            if "student" in lowered:
                _push("Student Records")
            if "course" in lowered:
                _push("Course Management")

            # Convert Activity class names into high-level feature hints.
            if name.endswith("Activity.java") or name.endswith("Activity.kt"):
                stem = name.rsplit(".", 1)[0]
                stem = stem.replace("Activity", "")
                words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", stem)
                label = " ".join(
                    w for w in words if w and w.lower() not in {"main"})
                if label and label.lower() not in low_signal:
                    _push(label)

        return inferred[:20]

    def _infer_themes_from_tags(self, tags: list[str]) -> list[str]:
        """
        Infer concise themes from tags when theme extraction is unavailable.
        """
        theme_candidates: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            term = str(tag or "").strip()
            if not term:
                continue
            lowered = term.lower()
            if lowered in seen:
                continue
            # Keep concise, human-readable thematic terms.
            if len(term.split()) <= 4 and len(term) <= 40:
                seen.add(lowered)
                theme_candidates.append(term)
        return theme_candidates[:10]

    def _infer_tone_fallback(self, tags: list[str], themes: list[str], file_reports) -> str | None:
        """
        Infer a conservative project tone when README tone is unavailable.
        """
        corpus_parts: list[str] = [str(x)
                                   for x in (tags + themes) if str(x).strip()]
        for fr in file_reports:
            corpus_parts.append(str(getattr(fr, "filepath", "") or ""))
        corpus = " ".join(corpus_parts).lower()

        educational_terms = {
            "tutorial", "learning", "phonics", "education", "student",
            "course", "training", "reference", "paper", "analysis",
        }
        experimental_terms = {
            "prototype", "experiment", "research", "bayesian", "evaluation",
            "benchmark", "lab", "model",
        }
        if any(term in corpus for term in experimental_terms):
            return "Experimental"
        if any(term in corpus for term in educational_terms):
            return "Educational"
        if corpus.strip():
            return "Professional"
        return None

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        tags: list[str] = []
        tag_seen: set[str] = set()
        theme_counts: dict[str, int] = {}
        tone_counts: dict[str, int] = {}
        readme_texts: list[str] = []

        for file_report in report.file_reports:
            keyphrases = file_report.get_value(
                FileStatCollection.README_KEYPHRASES.value
            )
            if keyphrases:
                for phrase in keyphrases:
                    normalized = phrase.strip().lower()
                    if not normalized or normalized in tag_seen:
                        continue
                    tag_seen.add(normalized)
                    tags.append(phrase)

            tone = file_report.get_value(
                FileStatCollection.README_TONE.value
            )
            if tone:
                tone_counts[tone] = tone_counts.get(tone, 0) + 1

            filename = Path(file_report.filepath).name.lower()
            if filename.startswith("readme"):
                try:
                    readme_path = Path(file_report.filepath)
                    if not readme_path.is_absolute():
                        readme_path = Path(report.project_path) / readme_path
                    if not readme_path.exists():
                        logger.info(
                            "README path not found for themes: %s", readme_path
                        )
                        continue
                    readme_texts.append(
                        readme_path.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        )
                    )
                except Exception:
                    logger.exception(
                        "Failed to read README for themes: %s",
                        file_report.filepath,
                    )

        if readme_texts:
            themes_by_doc = readme_insights.extract_readme_themes_bulk(
                readme_texts)
            empty_theme_count = sum(
                1 for themes in themes_by_doc if not themes)
            if empty_theme_count:
                logger.info(
                    "README theme extraction returned no themes for %d/%d documents in %s",
                    empty_theme_count,
                    len(themes_by_doc),
                    report.project_name,
                )
            for themes in themes_by_doc:
                for theme in set(themes):
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1
        else:
            logger.info(
                "No README files found for theme extraction in project %s",
                report.project_name,
            )

        # Dynamic fallback: infer tags/themes from source structure when README
        # signals are missing (e.g., mobile projects without README files).
        if not tags:
            inferred_tags = self._infer_tags_from_paths(report.file_reports)
            if inferred_tags:
                tags.extend(inferred_tags)
                logger.info(
                    "[README_INSIGHTS][%s] inferred %d tags from file paths",
                    report.project_name,
                    len(inferred_tags),
                )
        if not theme_counts and tags:
            inferred_themes = self._infer_themes_from_tags(tags)
            for theme in inferred_themes:
                theme_counts[theme] = 1
            if inferred_themes:
                logger.info(
                    "[README_INSIGHTS][%s] inferred %d themes from non-README signals",
                    report.project_name,
                    len(inferred_themes),
                )

        stats: list[Statistic] = []

        if tags:
            stats.append(
                Statistic(ProjectStatCollection.PROJECT_TAGS.value, tags)
            )

        if theme_counts:
            ranked_themes = sorted(
                theme_counts.items(), key=lambda kv: (-kv[1], kv[0])
            )
            stats.append(
                Statistic(
                    ProjectStatCollection.PROJECT_THEMES.value,
                    [name for name, _count in ranked_themes],
                )
            )

        majority_tone = self._pick_majority(tone_counts)
        if not majority_tone:
            majority_tone = self._infer_tone_fallback(
                tags,
                [name for name in theme_counts.keys()],
                report.file_reports,
            )
            if majority_tone:
                logger.info(
                    "[README_INSIGHTS][%s] inferred fallback tone=%s from non-README signals",
                    report.project_name,
                    majority_tone,
                )
        if majority_tone:
            stats.append(
                Statistic(ProjectStatCollection.PROJECT_TONE.value,
                          majority_tone)
            )

        logger.info(
            "[README_INSIGHTS][%s] readmes=%d tags=%d themes=%d tones=%d majority_tone=%s",
            report.project_name,
            len(readme_texts),
            len(tags),
            len(theme_counts),
            sum(tone_counts.values()),
            majority_tone or "None",
        )

        return stats


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

    Additonally returns the activity type ratio for the project which can be used as a comparison for the user
    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        activity_type_to_lines = {}
        average_activity_type_to_lines = {}

        git_analysis = True if report.email and report.project_repo else False

        for fr in report.file_reports:
            file_domain = fr.get_value(FileStatCollection.TYPE_OF_FILE.value)

            lines_in_file = fr.get_value(
                FileStatCollection.LINES_IN_FILE.value)

            if not file_domain or not lines_in_file:
                continue

            if fr.is_info_file:
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

            prev_count = average_activity_type_to_lines.get(file_domain, 0)

            average_activity_type_to_lines[file_domain] = prev_count + \
                lines_in_file

        normalize(activity_type_to_lines)
        normalize(average_activity_type_to_lines)

        return [Statistic(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value, activity_type_to_lines),
            Statistic(
                ProjectStatCollection.ACTIVITY_TYPE_RATIO.value, average_activity_type_to_lines)]


class ProjectAnalyzeGitAuthorship(ProjectStatisticCalculation):
    """
    Analyzes Git commit history to determine authorship statistics.
    This function uses `self.email` to calculate the user's commit percentage and the user's github account as a secondary check.
    If `self.email` is not set, this function should not run as we don't have
    the consent of the user.

    Creates the following project level statistics:
    - `IS_GROUP_PROJECT`: Boolean indicating if multiple authors contributed
    - `TOTAL_AUTHORS`: Total number of unique authors
    - `AUTHORS_PER_FILE`: Dictionary mapping file paths to number of unique authors
    - `USER_COMMIT_PERCENTAGE`: Percentage of commits made by the user (if applicable)
    - `GROUP CONTRIBUTIONS`: Dictionary mapping each other's email to commit count

    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        if not report.email or not report.project_repo:
            return []

        commit_count_by_author = self._get_commits_by_author(
            repo=report.project_repo
        )

        user_commits = [value for key, value in commit_count_by_author.items()
                        if key == report.email]

        total_commits = sum(commit_count_by_author.values())

        if total_commits == 0:
            return []

        # Calculate user's commit percentage
        user_commit_count = sum(user_commits) if user_commits else 0
        user_commit_percentage = round(
            (user_commit_count / total_commits) * 100, 2)

        # Determine if it's a group project
        num_authors = len(commit_count_by_author)
        is_group_project = num_authors > 1

        # Calculate authors per file
        authors_per_file = self._get_authors_per_file(report.project_repo)

        stats = [
            Statistic(
                ProjectStatCollection.IS_GROUP_PROJECT.value,
                is_group_project,
            ),
            Statistic(
                ProjectStatCollection.TOTAL_AUTHORS.value,
                num_authors,
            ),
            Statistic(
                ProjectStatCollection.AUTHORS_PER_FILE.value,
                authors_per_file,
            ),
        ]

        # Only add user commit percentage for group projects
        if is_group_project:
            group_contributions = self._get_commits_by_author(
                report.project_repo)

            stats.append(
                Statistic(
                    ProjectStatCollection.USER_COMMIT_PERCENTAGE.value,
                    user_commit_percentage,
                )
            )
            stats.append(
                Statistic(
                    ProjectStatCollection.GROUP_CONTRIBUTION.value,
                    group_contributions,
                )
            )

        return stats

    def _get_commits_by_author(self, repo) -> dict[str, int]:
        """Returns a dictionary mapping author emails to commit counts."""
        commit_count_by_author: dict[str, int] = {}
        for commit in repo.iter_commits():
            if hasattr(commit, "author") and hasattr(commit.author, "email"):
                email = commit.author.email
                commit_count_by_author[email] = (
                    commit_count_by_author.get(email, 0) + 1
                )
        return commit_count_by_author

    def _get_authors_per_file(self, repo) -> dict[str, int]:
        """Returns a dictionary mapping file paths to number of unique authors."""
        authors_per_file: dict[str, set[str]] = {}

        for commit in repo.iter_commits():
            if not hasattr(commit, "author") or not hasattr(commit.author, "email"):
                continue

            author_email = commit.author.email

            # Get files changed in this commit
            if commit.parents:
                diffs = commit.parents[0].diff(commit)
                for diff in diffs:
                    # Use b_path for new/modified files
                    file_path = diff.b_path if diff.b_path else diff.a_path
                    if file_path:
                        if file_path not in authors_per_file:
                            authors_per_file[file_path] = set()
                        authors_per_file[file_path].add(author_email)
            else:
                # First commit, all files are new
                for item in commit.tree.traverse():
                    if item.type == "blob":  # It's a file
                        if item.path not in authors_per_file:
                            authors_per_file[item.path] = set()
                        authors_per_file[item.path].add(author_email)

        # Convert sets to counts
        return {path: len(authors) for path, authors in authors_per_file.items()}


class ProjectContributionPatterns(ProjectStatisticCalculation):
    """
    Analyze commit patterns (types, work cadence, collaboration role) for the user via Azure OpenAI.
    Produces:
      - COMMIT_TYPE_DISTRIBUTION   (dict[str, float])
      - WORK_PATTERN               (str)
      - COLLABORATION_ROLE         (str)
      - ACTIVITY_METRICS           (dict[str, float])
      - ROLE_DESCRIPTION           (str)
    """

    def calculate(self, report: ProjectReport) -> list[Statistic]:
        logger.info(
            f"ProjectContributionPatterns.calculate called for {report.project_name}")

        if not report.project_repo or not report.email:
            logger.info(
                "Skipping contribution pattern analysis: no repo or email")
            return []

        if not azure_openai_enabled():
            logger.info(
                "Skipping contribution pattern analysis: Azure OpenAI disabled")
            return []

        try:
            user_commits = [
                c for c in report.project_repo.iter_commits()
                if getattr(c, "author", None) and getattr(c.author, "email", None) == report.email
            ]

            if not user_commits:
                logger.info(
                    f"No commits found for {report.email} in {report.project_name}")
                return []

            # Extract context for the LLM
            user_commit_pct = report.get_value(
                ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)
            total_authors = report.get_value(
                ProjectStatCollection.TOTAL_AUTHORS.value) or 1
            is_group = report.get_value(
                ProjectStatCollection.IS_GROUP_PROJECT.value) or False

            # Cap commits to avoid token limit bloat (e.g., take the most recent 100)
            # You can adjust this limit based on your Azure deployment's context window.
            commit_data = [
                {
                    "message": c.message.strip(),
                    "date": str(datetime.fromtimestamp(c.authored_date))
                }
                for c in user_commits[:100]
            ]

            # Assemble the facts payload
            facts = {
                "project_name": report.project_name,
                "user_email": report.email,
                "user_commit_percentage": user_commit_pct,
                "total_authors": total_authors,
                "is_group_project": is_group,
                "total_user_commits_analyzed": len(commit_data),
                "commits_sample": commit_data
            }

            # Call the Foundry Manager
            foundry = AzureFoundryManager()
            response = foundry.process_request(
                user_input=f"FACTS_JSON: {json.dumps(facts, ensure_ascii=True)}",
                system_prompt=CONTRIBUTION_PATTERN_PROMPT,
                response_model=ContributionPatternOutput,
                schema_name="contribution_patterns",
                max_tokens=400,  # Increased slightly to accommodate dicts and descriptions
                temperature=0.1  # Keep low for analytical consistency
            )

            if response is None:
                logger.warning(
                    f"Azure generation returned no structured response for {report.project_name}"
                )
                return []

            logger.info(
                f"Azure contribution pattern analysis completed for {report.project_name}: "
                f"role={response.collaboration_role}, pattern={response.work_pattern}"
            )

            stats = [
                Statistic(
                    ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value,
                    response.commit_type_distribution.model_dump()
                ),
                Statistic(
                    ProjectStatCollection.WORK_PATTERN.value,
                    response.work_pattern
                ),
                Statistic(
                    ProjectStatCollection.COLLABORATION_ROLE.value,
                    response.collaboration_role
                ),
                Statistic(
                    ProjectStatCollection.ACTIVITY_METRICS.value,
                    response.activity_metrics.model_dump()
                ),
                Statistic(
                    ProjectStatCollection.ROLE_DESCRIPTION.value,
                    response.role_description
                ),
            ]
            return stats

        except Exception as e:
            logger.error(
                f"Azure contribution pattern analysis failed for {report.project_name}: {e}",
                exc_info=True
            )
            return []


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
                if f not in IGNORE_FILES:
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

    def __init__(self, calculator_classes: Optional[list[Type]] = None) -> None:
        all_calculator_classes = [
            ProjectDates,
            CodingLanguageRatio,
            ProjectWeightedSkills,
            ProjectReadmeInsights,
            ProjectActivityTypeContributions,
            ProjectAnalyzeGitAuthorship,
            ProjectTotalContributionPercentage,
            ProjectContributionPatterns,
        ]

        # If specific calculator classes are requested, filter to only those
        if calculator_classes is not None:

            if len(calculator_classes) == 0:
                logger.warning(
                    "ProjectStatisticReportBuilder was called with no requested calulators. Was this intended?")
                self.calculators = []

                return

            self.calculators = [
                cls() for cls in all_calculator_classes
                if cls in calculator_classes
            ]
        else:
            self.calculators = [cls() for cls in all_calculator_classes]

        logger.info(
            f"ProjectStatisticReportBuilder initialized with {len(self.calculators)} calculators")
        logger.info(
            f"Calculators: {[type(c).__name__ for c in self.calculators]}")

    def build(self, report: ProjectReport) -> List[Statistic]:
        """
        Compile all the project level statistics together into one
        statistic list. We overide build because the statistic index
        attribute is called "project_statistics" in a project report.
        """

        stats: List[Statistic] = []

        for calc in self.calculators:

            new_stats = calc.calculate(report)

            if new_stats:
                report.project_statistics.extend(new_stats)
                stats.extend(new_stats)

        return stats
