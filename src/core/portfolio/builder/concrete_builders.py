from datetime import datetime
import re

from src.core.report import UserReport
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextListBlock, TextBlock
from src.core.portfolio.builder.build_system import PortfolioSectionBuilder
from src.utils.data_processing import fmt_mdy_short, fmt_mdy
from src.core.statistic import ProjectStatCollection, UserStatCollection
from src.core.ML.models.contribution_analysis import (
    generate_project_summary,
    build_project_summary_facts,
)


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

        The builder attempts ML generation first (grounded by structured facts),
        then falls back to deterministic phrasing if ML is unavailable or fails.
        """
        facts = self._build_project_summary_facts(project_report)
        if not facts:
            return None
        summary = generate_project_summary(facts)
        if summary and self._is_summary_well_formed(summary) and self._summary_covers_requirements(summary, facts):
            return summary

        fallback = self._build_project_summary_deterministic(facts)
        if fallback and self._is_summary_well_formed(fallback) and self._summary_covers_requirements(fallback, facts):
            return fallback
        return None

    def _build_project_summary_facts(self, project_report) -> dict | None:
        """Extract trusted stats into a compact facts payload for summary generation."""
        project_name = getattr(project_report, "project_name", None)

        themes = project_report.get_value(ProjectStatCollection.PROJECT_THEMES.value) or []
        tags = project_report.get_value(ProjectStatCollection.PROJECT_TAGS.value) or []
        goal_terms = self._select_goal_terms(project_name, themes, tags)

        frameworks = project_report.get_value(ProjectStatCollection.PROJECT_FRAMEWORKS.value)
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

        lang_ratio = project_report.get_value(ProjectStatCollection.CODING_LANGUAGE_RATIO.value)
        language_names: list[str] = []
        if lang_ratio:
            ranked_langs = sorted(lang_ratio.items(), key=lambda kv: kv[1], reverse=True)
            language_names = [getattr(lang, "value", str(lang)) for lang, _ in ranked_langs[:2]]

        role = project_report.get_value(ProjectStatCollection.COLLABORATION_ROLE.value)
        role_text = str(getattr(role, "value", role)) if role else None
        role_description = project_report.get_value(ProjectStatCollection.ROLE_DESCRIPTION.value)

        commit_dist = project_report.get_value(ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value)
        commit_focus = self._top_commit_focus(commit_dist)
        commit_pct = project_report.get_value(ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)
        line_pct = project_report.get_value(ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)
        activity_breakdown = self._activity_breakdown(project_report)

        if not goal_terms and not framework_names and not language_names and not role_description and not activity_breakdown:
            return None

        return build_project_summary_facts(
            project_name=project_name,
            goal_terms=goal_terms,
            frameworks=framework_names,
            languages=language_names,
            role=role_text,
            commit_focus=commit_focus,
            commit_pct=commit_pct if isinstance(commit_pct, (int, float)) else None,
            line_pct=line_pct if isinstance(line_pct, (int, float)) else None,
            activity_breakdown=activity_breakdown,
            role_description=str(role_description).strip() if role_description else None,
        )

    def _build_project_summary_deterministic(self, facts: dict) -> str | None:
        """Fallback summary generator using only local deterministic templates."""
        goal_terms = facts.get("goal_terms", [])
        frameworks = facts.get("frameworks", [])
        languages = facts.get("languages", [])
        role_description = facts.get("role_description")
        role = facts.get("role")
        commit_focus = facts.get("commit_focus")
        commit_pct = facts.get("commit_pct")
        line_pct = facts.get("line_pct")
        activity_breakdown = facts.get("activity_breakdown", [])

        goal_sentence = None
        if goal_terms:
            top = goal_terms[:2]
            if len(top) == 1:
                goal_sentence = f"The project had a primary goal of {top[0]}."
            else:
                goal_sentence = f"The project had primary goals of {top[0]} and {top[1]}."
        else:
            project_name = str(facts.get("project_name", "")).strip()
            if project_name:
                normalized_name = project_name.replace("-", " ").replace("_", " ").lower()
                goal_sentence = f"The project targeted {normalized_name} outcomes."
            else:
                goal_sentence = "The project targeted a clearly scoped product outcome."

        stack_sentence = None
        if frameworks and languages:
            stack_sentence = (
                f"It was implemented with {self._join_english(frameworks[:3])} and primarily written in "
                f"{self._join_english(languages[:2])}."
            )
        elif frameworks:
            stack_sentence = f"It was implemented with {self._join_english(frameworks[:3])}."
        elif languages:
            stack_sentence = f"It was primarily written in {self._join_english(languages[:2])}."
        else:
            stack_sentence = "The implementation stack was selected to match the project requirements."

        contribution_sentence = None
        if role_description:
            contribution_sentence = role_description.rstrip(".") + "."
        else:
            contribution_sentence = self._compose_contribution_sentence(
                role=role,
                commit_focus=commit_focus,
                commit_pct=commit_pct,
                line_pct=line_pct,
                activity_breakdown=activity_breakdown,
            )

        sentences = [s for s in [goal_sentence, stack_sentence, contribution_sentence] if s]
        if len(sentences) < 2:
            return None
        return " ".join(sentences[:3])

    def _select_goal_terms(self, project_name: str | None, themes, tags) -> list[str]:
        """
        Select concise goal terms and filter repeated project-name variants.
        """
        project_tokens = self._token_set(project_name or "")
        raw_terms = [str(x).strip() for x in list(themes) + list(tags) if str(x).strip()]

        selected: list[str] = []
        selected_tokens: list[set[str]] = []
        for term in raw_terms:
            term_tokens = self._token_set(term)
            if not term_tokens:
                continue
            if project_tokens:
                overlap = len(term_tokens & project_tokens) / len(term_tokens)
                if overlap >= 0.6:
                    continue
            if any(self._jaccard(term_tokens, existing) >= 0.6 for existing in selected_tokens):
                continue

            selected.append(term)
            selected_tokens.append(term_tokens)
            if len(selected) >= 4:
                break

        return selected[:4]

    def _activity_breakdown(self, project_report) -> list[tuple[str, float]]:
        """Return sorted contribution activity breakdown as (domain, percentage)."""
        activity = project_report.get_value(ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value)
        if not activity:
            return []

        pairs: list[tuple[str, float]] = []
        for domain, value in activity.items():
            name = str(getattr(domain, "value", domain)).replace("_", " ").lower()
            pct = float(value) * 100 if float(value) <= 1.0 else float(value)
            pairs.append((name, pct))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs

    def _is_summary_well_formed(self, summary: str) -> bool:
        """Validate output shape for section rendering."""
        sentence_count = summary.count(".")
        word_count = len(summary.split())
        return 2 <= sentence_count <= 3 and 20 <= word_count <= 160

    def _summary_covers_requirements(self, summary: str, facts: dict) -> bool:
        """
        Ensure summary reflects available goal, stack, and contribution facts.
        """
        lowered = summary.lower()

        goal_terms = [str(x).lower() for x in facts.get("goal_terms", []) if str(x).strip()]
        if goal_terms and not any(term in lowered for term in goal_terms):
            return False

        stack_terms = [str(x).lower() for x in facts.get("frameworks", []) + facts.get("languages", []) if str(x).strip()]
        if stack_terms and not any(term in lowered for term in stack_terms):
            return False

        contribution_terms = self._contribution_anchor_terms(facts)
        if contribution_terms and not any(term in lowered for term in contribution_terms):
            return False
        return True

    def _contribution_anchor_terms(self, facts: dict) -> list[str]:
        """Build normalized anchors to verify contribution coverage."""
        terms: list[str] = []
        stopwords = {
            "and", "the", "with", "for", "from", "into", "onto", "across",
            "this", "that", "was", "were", "have", "has", "had", "project",
            "delivery", "work", "changes",
        }

        role = facts.get("role")
        if role:
            role_tokens = str(role).replace("_", " ").lower().split()
            terms.extend([t for t in role_tokens if len(t) >= 4 and t not in stopwords])

        commit_focus = facts.get("commit_focus")
        if commit_focus:
            focus_tokens = str(commit_focus).replace("_", " ").lower().split()
            terms.extend([t for t in focus_tokens if len(t) >= 4 and t not in stopwords])

        role_description = facts.get("role_description")
        if role_description:
            desc_tokens = self._token_set(str(role_description))
            terms.extend([t for t in desc_tokens if len(t) >= 4 and t not in stopwords])

        commit_pct = facts.get("commit_pct")
        if isinstance(commit_pct, (int, float)):
            pct_str = f"{int(round(float(commit_pct)))}%"
            terms.append(pct_str)

        line_pct = facts.get("line_pct")
        if isinstance(line_pct, (int, float)):
            pct_str = f"{int(round(float(line_pct)))}%"
            terms.append(pct_str)

        for domain, _pct in facts.get("activity_breakdown", [])[:2]:
            if domain:
                domain_tokens = str(domain).lower().split()
                terms.extend([t for t in domain_tokens if len(t) >= 4 and t not in stopwords])

        return [t for t in terms if t]

    def _compose_contribution_sentence(
        self,
        role: str | None,
        commit_focus: str | None,
        commit_pct: float | None,
        line_pct: float | None,
        activity_breakdown: list[tuple[str, float]] | None,
    ) -> str:
        """
        Compose a readable contribution sentence from available contribution metrics.
        """
        lead = "I contributed"
        role_text = str(role).replace("_", " ").strip() if role else None
        if role_text:
            lead += f" as a {role_text}"

        detail_phrases: list[str] = []
        if isinstance(commit_pct, (int, float)):
            detail_phrases.append(f"authoring about {commit_pct:.0f}% of commits")
        elif isinstance(line_pct, (int, float)):
            detail_phrases.append(f"accounting for about {line_pct:.0f}% of authored lines")

        if commit_focus:
            focus = str(commit_focus).replace("_", " ").strip().lower()
            detail_phrases.append(f"focusing on {focus} changes")

        activity_phrase = self._activity_phrase(activity_breakdown or [])
        if activity_phrase:
            detail_phrases.append(activity_phrase)

        if detail_phrases:
            return f"{lead}, {self._join_english(detail_phrases)}."
        return f"{lead} across project delivery tasks."

    def _activity_phrase(self, activity_breakdown: list[tuple[str, float]]) -> str | None:
        """Return concise, professional activity-distribution wording."""
        if not activity_breakdown:
            return None

        top = activity_breakdown[:2]
        if len(top) == 1:
            return f"primarily through {top[0][0]} work ({top[0][1]:.0f}%)"
        return (
            f"primarily through {top[0][0]} ({top[0][1]:.0f}%) and "
            f"{top[1][0]} ({top[1][1]:.0f}%) work"
        )

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

    def _token_set(self, text: str) -> set[str]:
        return set(t for t in re.findall(r"[a-z0-9]+", text.lower()) if t)

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)


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
