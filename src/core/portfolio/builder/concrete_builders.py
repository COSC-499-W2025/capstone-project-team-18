from datetime import datetime

from src.core.report import UserReport
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextListBlock, TextBlock
from src.core.portfolio.builder.build_system import PortfolioSectionBuilder
from src.utils.data_processing import fmt_mdy_short, fmt_mdy
from src.core.statistic import ProjectStatCollection, UserStatCollection


class UserDateSectionBuilder(PortfolioSectionBuilder):
    """
    Builds a PortfolioSection
    """

    section_id = "user_dates"
    section_title = "Your Journey"

    def create_blocks(self, report: UserReport) -> list[Block]:
        blocks = []

        start_date = report.get_value(UserStatCollection.USER_START_DATE.value)

        if start_date is not None:
            text = f"You started your first project on {fmt_mdy(start_date)}!"
            s_block = Block("start_date", TextBlock(text=text))
            blocks.append(s_block)

        end_date = report.get_value(UserStatCollection.USER_END_DATE.value)

        if end_date is not None:
            text = f"Your latest contribution was on {fmt_mdy(end_date)}."
            e_block = Block("end_date", TextBlock(text=text))
            blocks.append(e_block)

        return blocks


class UserSkillsSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with the user's top skills."""

    section_id = "user_skills"
    section_title = "Skills"

    def create_blocks(self, report: UserReport) -> list[Block]:
        blocks = []

        skills = report.get_value(UserStatCollection.USER_SKILLS.value)

        if skills:
            skills.sort()
            sorted_skill_names = [s.skill_name for s in skills]
            top_rated_block = Block("top_rated_skills", TextListBlock(
                items=sorted_skill_names))
            blocks.append(top_rated_block)

        skill_lines = self.get_chronological_skills(report)

        if skill_lines:
            chrono_block = Block("skills", TextListBlock(items=skill_lines))
            blocks.append(chrono_block)

        return blocks

    def get_chronological_skills(self, user_report: UserReport) -> list[str]:
        """
        Produce a chronological list of skills exercised by the user across all projects.

        Skills are inferred from PROJECT_SKILLS_DEMONSTRATED on each ProjectReport
        (i.e., the WeightedSkills list), and ordered by the earliest project start
        date in which they appear.

        Returns a list of formatted strings like:
            "Python — First exercised Jan 12, 2023"
        """
        project_reports = getattr(user_report, "project_reports", None)
        if not project_reports:
            return []

        # Map skill_name -> earliest datetime it appears in any project
        skill_first_seen = {}

        for pr in project_reports:
            start_dt = pr.get_value(
                ProjectStatCollection.PROJECT_START_DATE.value)
            skills = pr.get_value(
                ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)
            if not skills:
                continue

            for ws in skills:
                name = getattr(ws, "skill_name", None) or str(ws)
                if not name:
                    continue

                current_first = skill_first_seen.get(name)
                if current_first is None or (start_dt is not None and start_dt < current_first):
                    skill_first_seen[name] = start_dt

        if not skill_first_seen:
            return []

        # Sort skills: first by date (None at the end), then by name
        sorted_skills = sorted(
            skill_first_seen.items(),
            key=lambda item: (
                item[1] if item[1] is not None else datetime.max,
                item[0]
            )
        )

        # Format lines
        lines = [
            f"{name} — First exercised {fmt_mdy_short(dt) if dt else 'on an unknown date'}"
            for name, dt in sorted_skills
        ]

        return lines


class UserCodingLanguageRatioSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with the user's coding language breakdown."""

    section_id = "user_coding_languages"
    section_title = "Your Coding Languages"

    def create_blocks(self, report: UserReport) -> list[Block]:

        coding_lang_ratio = report.get_value(
            UserStatCollection.USER_CODING_LANGUAGE_RATIO.value)

        if coding_lang_ratio is None:
            return []

        langs_sorted = sorted(coding_lang_ratio.items(),
                              key=lambda x: x[1], reverse=True)

        parts = []
        for lang, ratio in langs_sorted:
            lang_name = lang.value
            percent = f"{ratio * 100:.2f}%"
            parts.append(f"{lang_name} ({percent})")

        return [Block("coding_lang_ratio", TextListBlock(items=parts))]


class UserGenericStatisticsSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with other user statistics not specifically handled."""

    section_id = "user_statistics"
    section_title = "Additional Statistics"

    def create_blocks(self, report: UserReport) -> list[Block]:

        lines = []

        # Skip specific stats that are handled by other builders
        skip_names = {
            UserStatCollection.USER_START_DATE.value.name,
            UserStatCollection.USER_END_DATE.value.name,
            UserStatCollection.USER_SKILLS.value.name,
            UserStatCollection.USER_CODING_LANGUAGE_RATIO.value.name,
        }

        for stat in report.statistics:
            template = stat.get_template()
            name = template.name

            if name in skip_names:
                continue

            value = stat.value
            title = name.replace("_", " ").replace(
                "-", " ").strip().lower().title()

            should_try_date = (
                template.expected_type in (datetime, type(None))
                or isinstance(value, datetime)
            )

            if should_try_date:
                lines.append(f"{title}: {fmt_mdy(value)}")
            else:
                lines.append(f"{title}: {value!r}")

        if lines:
            block = Block("stats", TextListBlock(items=lines))
            return [block]

        return []


class ChronologicalProjectsSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with projects in chronological order."""

    section_title = "Projects in Chronological Order"
    section_id = "chrono_projects"

    def create_blocks(self, report: UserReport) -> list[Block]:
        project_lines = self.get_chronological_projects(report)

        if project_lines:
            block = Block("projects", TextListBlock(items=project_lines))
            return [block]

        return []

    def get_chronological_projects(self, user_report: UserReport) -> list[str]:
        """
        Return the user's projects ordered by start date.
        """
        if not getattr(user_report, "project_reports", None):
            return []

        entries = []
        for pr in user_report.project_reports:
            title = getattr(pr, "project_name", None) or "Untitled Project"
            start_dt = pr.get_value(
                ProjectStatCollection.PROJECT_START_DATE.value)
            end_dt = pr.get_value(ProjectStatCollection.PROJECT_END_DATE.value)

            if start_dt:
                formatted = f"{title} - Started {fmt_mdy_short(start_dt)}"
            else:
                formatted = f"{title} - Start date unknown"

            if end_dt:
                formatted += f" (Ended {fmt_mdy_short(end_dt)})"
            else:
                formatted += " (End date unknown)"

            entries.append(
                {"title": title, "start_date": start_dt, "formatted": formatted})

        dated = [e for e in entries if e["start_date"] is not None]
        undated = [e for e in entries if e["start_date"] is None]

        # Sort dated projects by start_date (oldest -> newest)
        dated.sort(key=lambda e: e["start_date"])

        ordered = dated + undated

        # Build numbered lines
        lines = [f"{i+1}. {e['formatted']}" for i, e in enumerate(ordered)]

        return lines


class ProjectSummariesSectionBuilder(PortfolioSectionBuilder):
    """
    Builds a section with deterministic, grounded textual summaries per project.

    Each project summary targets 2-3 sentences and is composed from trusted
    project statistics only: goals (themes/tags), stack (frameworks/languages),
    and contribution (role/commit focus/contribution percentages).
    """

    section_id = "project_summaries"
    section_title = "Project Summaries"

    def create_blocks(self, report: UserReport) -> list[Block]:
        summary_lines = self.get_project_summaries(report)

        if summary_lines:
            block = Block("project_summaries", TextListBlock(items=summary_lines))
            return [block]

        return []

    def get_project_summaries(self, user_report: UserReport) -> list[str]:
        """
        Return one summary line per project:
            "Project Name: sentence one. sentence two. [sentence three.]"
        """
        if not getattr(user_report, "project_reports", None):
            return []

        lines: list[str] = []
        for pr in user_report.project_reports:
            summary = self._build_project_summary(pr)
            if not summary:
                continue
            title = getattr(pr, "project_name", None) or "Untitled Project"
            lines.append(f"{title}: {summary}")
        return lines

    def _build_project_summary(self, project_report) -> str | None:
        """
        Compose a 2-3 sentence grounded summary from project statistics.

        The function only uses existing computed stats and never invents new
        technologies/goals/contributions.
        """
        goal_sentence = self._goal_sentence(project_report)
        stack_sentence = self._stack_sentence(project_report)
        contribution_sentence = self._contribution_sentence(project_report)

        sentences = [s for s in [goal_sentence, stack_sentence, contribution_sentence] if s]
        if len(sentences) < 2:
            return None
        return " ".join(sentences[:3])

    def _goal_sentence(self, project_report) -> str | None:
        """Build a sentence describing project goals/themes from README-derived stats."""
        themes = project_report.get_value(ProjectStatCollection.PROJECT_THEMES.value)
        tags = project_report.get_value(ProjectStatCollection.PROJECT_TAGS.value)

        if themes:
            top_themes = [str(t) for t in themes[:2]]
            if len(top_themes) == 1:
                return f"The project goals centered on {top_themes[0]}."
            return f"The project goals centered on {top_themes[0]} and {top_themes[1]}."

        if tags:
            top_tags = [str(t) for t in tags[:3]]
            if len(top_tags) == 1:
                return f"A primary project goal was {top_tags[0]}."
            if len(top_tags) == 2:
                return f"Primary goals included {top_tags[0]} and {top_tags[1]}."
            return f"Primary goals included {top_tags[0]}, {top_tags[1]}, and {top_tags[2]}."

        return None

    def _stack_sentence(self, project_report) -> str | None:
        """Build a sentence describing frameworks and core implementation languages."""
        frameworks = project_report.get_value(ProjectStatCollection.PROJECT_FRAMEWORKS.value)
        lang_ratio = project_report.get_value(ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

        framework_names: list[str] = []
        if frameworks:
            ranked_frameworks = sorted(
                frameworks,
                key=lambda ws: getattr(ws, "weight", 0),
                reverse=True,
            )
            framework_names = [
                getattr(ws, "skill_name", str(ws)) for ws in ranked_frameworks[:3]
            ]

        language_names: list[str] = []
        if lang_ratio:
            ranked_langs = sorted(lang_ratio.items(), key=lambda kv: kv[1], reverse=True)
            language_names = [
                getattr(lang, "value", str(lang)) for lang, _ in ranked_langs[:2]
            ]

        if framework_names and language_names:
            return (
                f"The implementation used {self._join_english(framework_names)} with primary languages "
                f"{self._join_english(language_names)}."
            )
        if framework_names:
            return f"The implementation used {self._join_english(framework_names)}."
        if language_names:
            return f"Primary implementation languages were {self._join_english(language_names)}."
        return None

    def _contribution_sentence(self, project_report) -> str | None:
        """Build a sentence describing role and measurable contribution."""
        role = project_report.get_value(ProjectStatCollection.COLLABORATION_ROLE.value)
        role_description = project_report.get_value(ProjectStatCollection.ROLE_DESCRIPTION.value)
        commit_dist = project_report.get_value(ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value)
        commit_pct = project_report.get_value(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)
        line_pct = project_report.get_value(ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)

        if role_description:
            return str(role_description).strip().rstrip(".") + "."

        pieces: list[str] = []
        if role:
            role_phrase = str(getattr(role, "value", role)).replace("_", " ")
            pieces.append(f"as a {role_phrase}")

        if isinstance(commit_pct, (int, float)):
            pieces.append(f"contributing about {commit_pct:.0f}% of commits")
        elif isinstance(line_pct, (int, float)):
            pieces.append(f"contributing about {line_pct:.0f}% of authored lines")

        commit_focus = self._top_commit_focus(commit_dist)
        if commit_focus:
            pieces.append(f"with most work in {commit_focus} changes")

        if not pieces:
            return None
        return f"My contribution was primarily {self._join_english(pieces)}."

    def _top_commit_focus(self, commit_dist) -> str | None:
        """Return the dominant commit type label from a distribution dict."""
        if not commit_dist:
            return None
        top = sorted(commit_dist.items(), key=lambda kv: kv[1], reverse=True)
        if not top:
            return None
        label = str(top[0][0]).replace("_", " ").strip().lower()
        return label if label else None

    def _join_english(self, items: list[str]) -> str:
        """Join phrases with natural English conjunctions."""
        clean = [i for i in items if i]
        if not clean:
            return ""
        if len(clean) == 1:
            return clean[0]
        if len(clean) == 2:
            return f"{clean[0]} and {clean[1]}"
        return f"{', '.join(clean[:-1])}, and {clean[-1]}"


class ProjectTagsSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with project tags."""

    section_id = "project_tags"
    section_title = "Project Tags"

    def create_blocks(self, report: UserReport) -> list[Block]:
        tag_lines = self.get_project_tags(report)

        if tag_lines:
            block = Block("tags", TextListBlock(items=tag_lines))
            return [block]

        return []

    def get_project_tags(self, user_report: UserReport) -> list[str]:
        """
        Return a list of per-project tag lines:
            "Project Name: tag1, tag2, tag3"
        """
        if not getattr(user_report, "project_reports", None):
            return []

        lines = []
        for pr in user_report.project_reports:
            tags = pr.get_value(ProjectStatCollection.PROJECT_TAGS.value)
            if not tags:
                continue
            lines.append(f"{pr.project_name}: {', '.join(tags)}")

        return lines


class ProjectThemesSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with project themes."""

    section_id = "project_themes"
    section_title = "Project Themes"

    def create_blocks(self, report: UserReport) -> list[Block]:
        themes = self.get_project_themes(report)

        if themes:
            block = Block("themes", TextListBlock(items=themes))
            return [block]

        return []

    def get_project_themes(self, user_report: UserReport) -> list[str]:
        """
        Return a list of per-project theme lines:
            "Project Name: theme1, theme2"
        """
        if not getattr(user_report, "project_reports", None):
            return []

        lines = []
        for pr in user_report.project_reports:
            themes = pr.get_value(ProjectStatCollection.PROJECT_THEMES.value)
            if not themes:
                continue
            lines.append(f"{pr.project_name}: {', '.join(themes)}")

        return lines


class ProjectTonesSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with project tones."""

    section_id = "project_tones"
    section_title = "Project Tone"

    def create_blocks(self, report: UserReport) -> list[Block]:
        tone_lines = self.get_project_tones(report)

        if tone_lines:
            block = Block("tones", TextListBlock(items=tone_lines))
            return [block]

        return []

    def get_project_tones(self, user_report: UserReport) -> list[str]:
        """
        Return a list of per-project tone lines:
            "Project Name: Professional"
        """
        if not getattr(user_report, "project_reports", None):
            return []

        lines = []
        for pr in user_report.project_reports:
            tone = pr.get_value(ProjectStatCollection.PROJECT_TONE.value)
            if not tone:
                continue
            lines.append(f"{pr.project_name}: {tone}")

        return lines


class ProjectActivityMetricsSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with per-project activity metrics."""

    section_id = "project_activity_metrics"
    section_title = "Activity Metrics"

    def create_blocks(self, report: UserReport) -> list[Block]:
        activity_lines = self.get_project_activity_metrics(report)

        if activity_lines:
            block = Block("activity_metrics",
                          TextListBlock(items=activity_lines))
            return [block]

        return []

    def get_project_activity_metrics(self, user_report: UserReport) -> list[str]:
        """
        Return a list of per-project activity metrics:
            "Project Name: 5.2 commits/week, consistency 0.85"
        """
        if not getattr(user_report, "project_reports", None):
            return []

        lines = []
        for pr in user_report.project_reports:
            activity = pr.get_value(
                ProjectStatCollection.ACTIVITY_METRICS.value)
            if not activity:
                continue

            cpw = activity.get("avg_commits_per_week")
            cons = activity.get("consistency_score")
            parts = []
            if cpw is not None:
                parts.append(f"{cpw:.1f} commits/week")
            if cons is not None:
                parts.append(f"consistency {cons:.2f}")

            activity_str = ", ".join(
                parts) if parts else "activity data unavailable"
            lines.append(f"{pr.project_name}: {activity_str}")

        return lines


class ProjectCommitFocusSectionBuilder(PortfolioSectionBuilder):
    """Builds a section with per-project commit type distributions."""

    section_id = "project_commit_focus"
    section_title = "Commit Focus"

    def create_blocks(self, report: UserReport) -> list[Block]:
        commit_lines = self.get_project_commit_focus(report)

        if commit_lines:
            block = Block("commit_focus", TextListBlock(items=commit_lines))
            return [block]

        return []

    def get_project_commit_focus(self, user_report: UserReport) -> list[str]:
        """
        Return a list of per-project commit type distributions:
            "Project Name: Feature 45%, Bugfix 30%, Documentation 25%"
        """
        if not getattr(user_report, "project_reports", None):
            return []

        lines = []
        for pr in user_report.project_reports:
            commit_dist = pr.get_value(
                ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value)
            if not commit_dist:
                continue

            top = sorted(commit_dist.items(),
                         key=lambda kv: kv[1], reverse=True)
            commit_str = ", ".join(
                f"{k.title()} {v:.0f}%" for k, v in top if v > 0)
            if not commit_str:
                commit_str = "no commit data"
            lines.append(f"{pr.project_name}: {commit_str}")

        return lines
