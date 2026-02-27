from datetime import datetime
import os
import re

from src.core.report import UserReport
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextListBlock, TextBlock
from src.core.portfolio.builder.build_system import PortfolioSectionBuilder
from src.utils.data_processing import fmt_mdy_short, fmt_mdy
from src.core.statistic import ProjectStatCollection, UserStatCollection
from src.core.statistic.skills import SkillMapper
from src.core.ML.models.contribution_analysis import (
    generate_signature,
    build_signature_facts,
    resolve_experience_stage_with_ml,
    generate_project_summary,
    build_project_summary_facts,
    configure_project_summary_run,
)
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _summary_diagnostics_enabled() -> bool:
    """Enable detailed per-project summary diagnostics."""
    raw = os.environ.get("ARTIFACT_MINER_SUMMARY_DIAGNOSTICS", "0")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


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


class UserSummarySectionBuilder(PortfolioSectionBuilder):
    """Builds a section with the user's summary."""

    section_id = "summary"
    section_title = "Summary"

    def create_blocks(self, report: UserReport) -> list[Block]:
        # Build a dynamic signature from current report data (no DB storage).
        signature = self._build_signature(report)

        if not signature or not isinstance(signature, str):
            return []

        signature = signature.strip()
        if not signature:
            return []

        return [Block("signature", TextBlock(text=signature))]

    def _build_signature(self, report: UserReport) -> str | None:
        """
        Build a summary by collecting user/project signals and calling the generator.

        The method intentionally works only from report statistics so the summary
        stays deterministic relative to analyzed project data.
        """
        lang_ratio = report.get_value(
            UserStatCollection.USER_CODING_LANGUAGE_RATIO.value
        )
        user_skills = report.get_value(UserStatCollection.USER_SKILLS.value)

        role = self._dominant_role(report)
        cadence = self._dominant_cadence(report)
        commit_focus = self._dominant_commit_focus(report)
        tools = self._top_tools(report, limit=6)

        top_langs = self._top_languages_list(lang_ratio, limit=4)
        top_skills = self._top_skills_list(user_skills, limit=6)
        themes = self._top_project_themes(report, limit=4)
        tags = self._top_project_tags(report, limit=8)
        focus = self._infer_focus(
            top_skills=top_skills,
            tools=tools,
            themes=themes,
            tags=tags,
            commit_focus=commit_focus,
        )
        activities = self._activity_signals(report, cadence, commit_focus)
        emerging = self._emerging_signals(top_skills, tools, themes, tags)
        baseline_stage = self._infer_experience_stage(report, role)
        start_date = report.get_value(UserStatCollection.USER_START_DATE.value)
        end_date = report.get_value(UserStatCollection.USER_END_DATE.value)
        active_months: float | None = None
        if start_date and end_date:
            active_months = abs((end_date - start_date).days) / 30.0
        tone_counts = self._project_tone_counts(report)
        experience_stage = resolve_experience_stage_with_ml(
            baseline_stage=baseline_stage,
            project_count=len(getattr(report, "project_reports", []) or []),
            active_months=active_months,
            role=role,
            top_skills=top_skills,
            top_languages=top_langs,
            tools=tools,
            professional_project_count=tone_counts.get("professional", 0),
            experimental_project_count=tone_counts.get("experimental", 0),
            educational_project_count=tone_counts.get("educational", 0),
        )
        project_names = [pr.project_name for pr in report.project_reports if getattr(pr, "project_name", None)]

        facts = build_signature_facts(
            focus=focus,
            top_skills=top_skills,
            top_languages=top_langs,
            tools=tools,
            role=role,
            cadence=cadence,
            commit_focus=commit_focus,
            themes=themes,
            activities=activities,
            emerging=emerging,
            project_names=project_names,
            tags=tags,
            experience_stage=experience_stage,
        )

        signature = generate_signature(facts)
        if signature:
            if self._is_valid_summary(signature):
                return signature
            logger.warning(
                "Summary rejected by validator (len=%d, sentences=%d): %s",
                len(signature.split()),
                signature.count("."),
                signature[:200],
            )
            return None
        return None

    def _project_tone_counts(self, report: UserReport) -> dict[str, int]:
        """Aggregate project tones to support stage inference heuristics."""
        counts: dict[str, int] = {}
        for pr in report.project_reports:
            tone = pr.get_value(ProjectStatCollection.PROJECT_TONE.value)
            if not tone:
                continue
            tone_key = str(tone).strip().lower()
            counts[tone_key] = counts.get(tone_key, 0) + 1
        return counts

    def _dominant_role(self, report: UserReport) -> str | None:
        """Infer the user's dominant collaboration role across projects."""
        role_counts: dict[str, int] = {}
        for pr in report.project_reports:
            role = pr.get_value(ProjectStatCollection.COLLABORATION_ROLE.value)
            if role is None:
                continue
            role_key = getattr(role, "value", str(role))
            role_counts[role_key] = role_counts.get(role_key, 0) + 1
        if not role_counts:
            return None
        return max(role_counts.items(), key=lambda kv: kv[1])[0]

    def _dominant_cadence(self, report: UserReport) -> str | None:
        """Infer the most common work cadence across projects."""
        cadence_counts: dict[str, int] = {}
        for pr in report.project_reports:
            cadence = pr.get_value(ProjectStatCollection.WORK_PATTERN.value)
            if cadence is None:
                continue
            cadence_key = getattr(cadence, "value", str(cadence))
            cadence_counts[cadence_key] = cadence_counts.get(cadence_key, 0) + 1
        if not cadence_counts:
            return None
        return max(cadence_counts.items(), key=lambda kv: kv[1])[0]

    def _dominant_commit_focus(self, report: UserReport) -> str | None:
        """Infer top commit focus by aggregating commit type distributions."""
        totals: dict[str, float] = {}
        for pr in report.project_reports:
            dist = pr.get_value(
                ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value
            )
            if not dist:
                continue
            for k, v in dist.items():
                totals[k] = totals.get(k, 0.0) + float(v)
        if not totals:
            return None
        return max(totals.items(), key=lambda kv: kv[1])[0]

    def _top_tools(self, report: UserReport, limit: int) -> list[str]:
        """Aggregate framework/tool usage by weight and return top entries."""
        tools: dict[str, float] = {}
        for pr in report.project_reports:
            frameworks = pr.get_value(ProjectStatCollection.PROJECT_FRAMEWORKS.value)
            if not frameworks:
                continue
            for ws in frameworks:
                name = getattr(ws, "skill_name", None) or str(ws)
                weight = getattr(ws, "weight", 1.0)
                tools[name] = tools.get(name, 0.0) + float(weight)
        if not tools:
            return []
        ranked = sorted(tools.items(), key=lambda kv: kv[1], reverse=True)
        return [name for name, _ in ranked[:limit]]

    def _top_languages_list(self, lang_ratio, limit: int) -> list[str]:
        """Return top coding languages from user language ratio stats."""
        if not lang_ratio:
            return []
        ranked = sorted(lang_ratio.items(), key=lambda kv: kv[1], reverse=True)
        return [getattr(lang, "value", str(lang)) for lang, _ in ranked[:limit]]

    def _top_skills_list(self, user_skills, limit: int) -> list[str]:
        """Return top weighted user skills in descending order."""
        if not user_skills:
            return []
        ranked = sorted(
            user_skills, key=lambda s: getattr(s, "weight", 0), reverse=True
        )
        return [getattr(ws, "skill_name", str(ws)) for ws in ranked[:limit]]

    def _top_project_themes(self, report: UserReport, limit: int) -> list[str]:
        """Return most frequent inferred project themes across repositories."""
        themes: dict[str, int] = {}
        for pr in report.project_reports:
            project_themes = pr.get_value(ProjectStatCollection.PROJECT_THEMES.value)
            if not project_themes:
                continue
            for t in project_themes:
                themes[t] = themes.get(t, 0) + 1
        if not themes:
            return []
        ranked = sorted(themes.items(), key=lambda kv: kv[1], reverse=True)
        return [name for name, _ in ranked[:limit]]

    def _top_project_tags(self, report: UserReport, limit: int) -> list[str]:
        """Return most frequent README-derived project tags across repositories."""
        tags: dict[str, int] = {}
        for pr in report.project_reports:
            project_tags = pr.get_value(ProjectStatCollection.PROJECT_TAGS.value)
            if not project_tags:
                continue
            for t in project_tags:
                tags[t] = tags.get(t, 0) + 1
        if not tags:
            return []
        ranked = sorted(tags.items(), key=lambda kv: kv[1], reverse=True)
        return [name for name, _ in ranked[:limit]]

    def _infer_focus(
        self,
        top_skills: list[str],
        tools: list[str],
        themes: list[str],
        tags: list[str],
        commit_focus: str | None,
    ) -> str | None:
        """Infer a primary professional focus from skills, tools, and project signals."""
        focus_keywords = SkillMapper.summary_focus_keywords()

        def _normalize_tokens(items: list[str]) -> list[str]:
            tokens: list[str] = []
            for item in items:
                if not item:
                    continue
                normalized = re.sub(r"[^a-z0-9+# ]+", " ", str(item).lower())
                tokens.append(" ".join(normalized.split()))
            return tokens

        corpus = _normalize_tokens(top_skills + tools + themes + tags)
        if commit_focus:
            corpus.append(str(commit_focus).lower())

        scores = {focus: 0 for focus in focus_keywords}
        for text in corpus:
            for focus, keywords in focus_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        scores[focus] += 1

        best_focus = max(scores.items(), key=lambda kv: kv[1])
        if best_focus[1] <= 0:
            return None
        return best_focus[0]

    def _activity_signals(
        self,
        report: UserReport,
        cadence: str | None,
        commit_focus: str | None,
    ) -> list[str]:
        """
        Build human-readable activity signals for summary prompting.

        Signals combine categorical stats (cadence/commit focus) with numeric
        activity metrics so summary language can reflect execution style.
        """
        signals: list[str] = []

        cadence_map = {
            "consistent": "consistent delivery cadence",
            "sprint-based": "sprint-oriented execution",
            "burst": "burst-style iteration",
            "sporadic": "intermittent execution pattern",
        }
        if cadence and cadence in cadence_map:
            signals.append(cadence_map[cadence])

        commit_map = {
            "feature": "feature implementation",
            "bugfix": "reliability and bug resolution",
            "fix": "reliability and bug resolution",
            "docs": "documentation quality",
            "refactor": "code quality and maintainability",
            "test": "test coverage and verification",
            "chore": "engineering operations",
        }
        if commit_focus:
            lowered = str(commit_focus).lower()
            if lowered in commit_map:
                signals.append(commit_map[lowered])

        commits_per_week: list[float] = []
        consistency_scores: list[float] = []
        for pr in report.project_reports:
            activity = pr.get_value(ProjectStatCollection.ACTIVITY_METRICS.value)
            if not activity:
                continue
            cpw = activity.get("avg_commits_per_week")
            consistency = activity.get("consistency_score")
            if isinstance(cpw, (int, float)):
                commits_per_week.append(float(cpw))
            if isinstance(consistency, (int, float)):
                consistency_scores.append(float(consistency))

        if commits_per_week:
            avg_cpw = sum(commits_per_week) / len(commits_per_week)
            if avg_cpw >= 5.0:
                signals.append("high weekly delivery cadence")
            elif avg_cpw >= 2.0:
                signals.append("steady weekly delivery")

        if consistency_scores:
            avg_consistency = sum(consistency_scores) / len(consistency_scores)
            if avg_consistency >= 0.75:
                signals.append("consistent execution patterns")
            elif avg_consistency <= 0.40:
                signals.append("deadline-driven execution spikes")

        unique_signals = list(dict.fromkeys(signals))
        return unique_signals[:4]

    def _emerging_signals(
        self,
        top_skills: list[str],
        tools: list[str],
        themes: list[str],
        tags: list[str],
    ) -> list[str]:
        """
        Detect emerging capability areas from skill/tool/theme/tag text.

        These hints are used for optional forward-looking summary language.
        """
        corpus = " ".join(str(x) for x in (top_skills + tools + themes + tags) if x).lower()
        signals: list[str] = []

        for label, keywords in SkillMapper.summary_emerging_keywords().items():
            if any(keyword in corpus for keyword in keywords):
                signals.append(label)

        return signals[:3]

    def _infer_experience_stage(self, report: UserReport, role: str | None) -> str:
        """
        Infer summary tone profile: student, early-career, or experienced.
        Uses a weighted blend of project volume, active span, role, and
        PROJECT_TONE so a single old repository does not overstate experience.
        """
        project_count = len(getattr(report, "project_reports", []) or [])
        start_date = report.get_value(UserStatCollection.USER_START_DATE.value)
        end_date = report.get_value(UserStatCollection.USER_END_DATE.value)

        months_span: float | None = None
        if start_date and end_date:
            days = abs((end_date - start_date).days)
            months_span = days / 30.0

        score = 0.0

        # Project volume is the strongest long-term signal.
        if project_count >= 8:
            score += 3.0
        elif project_count >= 5:
            score += 2.0
        elif project_count >= 3:
            score += 1.0
        elif project_count <= 1:
            score -= 1.0

        # Active time span is supportive, but not enough on its own.
        if months_span is not None:
            if months_span >= 60:
                score += 2.0
            elif months_span >= 30:
                score += 1.0

        # Role signal nudges stage upward for leadership-heavy histories.
        if role:
            lowered_role = str(role).lower()
            if "leader" in lowered_role:
                score += 1.0
            elif "core_contributor" in lowered_role or "core contributor" in lowered_role:
                score += 0.5

        # Use existing README tone metric as an additional maturity signal.
        tone_counts: dict[str, int] = {}
        for pr in report.project_reports:
            tone = pr.get_value(ProjectStatCollection.PROJECT_TONE.value)
            if not tone:
                continue
            tone_key = str(tone).strip().lower()
            tone_counts[tone_key] = tone_counts.get(tone_key, 0) + 1

        professional_count = tone_counts.get("professional", 0)
        experimental_count = tone_counts.get("experimental", 0)
        educational_count = tone_counts.get("educational", 0)
        majority_threshold = max(1, project_count // 2)

        if professional_count >= majority_threshold and professional_count > experimental_count:
            score += 1.0
        if experimental_count >= majority_threshold and experimental_count > professional_count:
            score -= 0.5
        if educational_count >= majority_threshold and project_count <= 3:
            score -= 0.5

        if score >= 4.0 and project_count >= 4:
            stage = "experienced"
        elif score >= 1.5:
            stage = "early-career"
        else:
            stage = "student"

        # Guardrail: prevent single-project histories from being marked as experienced.
        if project_count <= 2 and stage == "experienced":
            stage = "early-career"

        return stage

    def _is_valid_summary(self, summary: str) -> bool:
        """Builder-level safety check before rendering summary block."""
        word_count = len(summary.split())
        sentence_count = summary.count(".")
        if word_count < 20 or word_count > 140:
            return False
        return 1 <= sentence_count <= 6


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

        configure_project_summary_run(len(user_report.project_reports))

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
            if _summary_diagnostics_enabled():
                logger.info(
                    "[PROJECT_SUMMARY][%s] skipped: no facts extracted",
                    getattr(project_report, "project_name", "unknown-project"),
                )
            return None
        require_ml = os.environ.get("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML") == "1"
        if _summary_diagnostics_enabled():
            logger.info(
                "[PROJECT_SUMMARY][%s] facts: goals=%d frameworks=%d languages=%d stack_hints=%d activity=%d allow_percentages=%s",
                getattr(project_report, "project_name", "unknown-project"),
                len(facts.get("goal_terms", []) or []),
                len(facts.get("frameworks", []) or []),
                len(facts.get("languages", []) or []),
                len(facts.get("stack_hints", []) or []),
                len(facts.get("activity_breakdown", []) or []),
                facts.get("allow_percentages"),
            )
        summary = generate_project_summary(facts)
        project_name = getattr(project_report, "project_name", "unknown-project")
        is_well_formed = bool(summary and self._is_summary_well_formed(summary))
        goal_ok = stack_ok = contribution_ok = True
        covers_requirements = False
        if summary:
            goal_ok, stack_ok, contribution_ok = self._summary_requirement_checks(summary, facts)
            covers_requirements = goal_ok and stack_ok and contribution_ok
        if (
            summary
            and is_well_formed
            and (require_ml or covers_requirements)
        ):
            if _summary_diagnostics_enabled():
                logger.info(
                    "[PROJECT_SUMMARY][%s] accepted: well_formed=%s covers_requirements=%s",
                    project_name,
                    is_well_formed,
                    covers_requirements,
                )
            return summary

        if summary:
            logger.info(
                (
                    "Project summary rejected at builder for %s "
                    "(well_formed=%s, covers_requirements=%s, goal_ok=%s, stack_ok=%s, contribution_ok=%s, require_ml=%s)"
                ),
                project_name,
                is_well_formed,
                covers_requirements,
                goal_ok,
                stack_ok,
                contribution_ok,
                require_ml,
            )
            if _summary_diagnostics_enabled():
                logger.info(
                    "[PROJECT_SUMMARY][%s] rejected summary text: %s",
                    project_name,
                    summary[:400],
                )

        if require_ml:
            return None

        fallback = self._build_project_summary_deterministic(facts)
        if fallback and self._is_summary_well_formed(fallback) and self._summary_covers_requirements(fallback, facts):
            if _summary_diagnostics_enabled():
                logger.info(
                    "[PROJECT_SUMMARY][%s] fallback accepted",
                    project_name,
                )
            return fallback
        if _summary_diagnostics_enabled():
            logger.info(
                "[PROJECT_SUMMARY][%s] fallback rejected/empty",
                project_name,
            )
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
        stack_hints = self._extract_stack_hints(themes, tags)
        for hint in stack_hints:
            if hint not in framework_names:
                framework_names.append(hint)
        framework_names = framework_names[:5]

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
            stack_hints=stack_hints,
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
        allow_percentages = bool(facts.get("allow_percentages"))

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
                allow_percentages=allow_percentages,
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
        deprioritize = {
            "ci", "cicd", "testing", "test", "configuration", "requirements", "known bugs",
            "startup scripts", "docker compose", "windows support", "macos support",
        }
        prioritize = {
            "student", "management", "records", "course", "itinerary", "trip", "event",
            "phonics", "pronunciation", "speech", "bayesian", "label", "transfer",
            "analysis", "dashboard", "visualization",
        }

        scored_terms: list[tuple[float, str, set[str]]] = []
        for term in raw_terms:
            term_tokens = self._token_set(term)
            if not term_tokens:
                continue
            if project_tokens:
                overlap = len(term_tokens & project_tokens) / len(term_tokens)
                if overlap >= 0.6:
                    continue
            score = 1.0
            if term_tokens & prioritize:
                score += 1.0
            if term_tokens & deprioritize:
                score -= 0.6
            if len(term_tokens) >= 2:
                score += 0.2
            scored_terms.append((score, term, term_tokens))

        scored_terms.sort(key=lambda x: x[0], reverse=True)

        selected: list[str] = []
        selected_tokens: list[set[str]] = []
        for _score, term, term_tokens in scored_terms:
            if any(self._jaccard(term_tokens, existing) >= 0.6 for existing in selected_tokens):
                continue
            selected.append(term)
            selected_tokens.append(term_tokens)
            if len(selected) >= 4:
                break

        return selected[:4]

    def _extract_stack_hints(self, themes, tags) -> list[str]:
        """Extract likely technical stack/service hints from README-derived terms."""
        terms = [str(x).strip() for x in list(themes) + list(tags) if str(x).strip()]
        hints: list[str] = []
        seen: set[str] = set()
        tech_keywords = {
            "react", "next", "tailwind", "azure", "speech", "sdk", "android",
            "androidx", "typescript", "javascript", "python", "java", "docker",
            "pytest", "tkinter", "fastapi", "sql", "postgres", "mongodb",
        }
        for term in terms:
            lowered = term.lower()
            token_set = self._token_set(term)
            if not token_set:
                continue
            if not (token_set & tech_keywords):
                continue
            if len(token_set) > 4:
                continue
            normalized = term.replace("next.js", "next").replace("typescript", "TypeScript").strip()
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            hints.append(normalized)
            if len(hints) >= 4:
                break
        return hints

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
        sentence_count = len(
            [
                segment.strip()
                for segment in re.split(r"(?:(?<!\d)\.|\.(?!\d)|[!?])+", summary or "")
                if segment and segment.strip()
            ]
        )
        word_count = len(summary.split())
        return 2 <= sentence_count <= 3 and 20 <= word_count <= 160

    def _summary_covers_requirements(self, summary: str, facts: dict) -> bool:
        """
        Ensure summary reflects available goal, stack, and contribution facts.
        """
        goal_ok, stack_ok, contribution_ok = self._summary_requirement_checks(summary, facts)
        return goal_ok and stack_ok and contribution_ok

    def _summary_requirement_checks(self, summary: str, facts: dict) -> tuple[bool, bool, bool]:
        """
        Return per-anchor requirement checks for goal, stack, and contribution.
        """
        lowered = str(summary or "").lower()

        goal_terms = [str(x).lower() for x in facts.get("goal_terms", []) if str(x).strip()]
        goal_ok = (not goal_terms) or self._goal_anchor_matches(summary, goal_terms)

        stack_terms = [
            str(x).lower()
            for x in facts.get("frameworks", []) + facts.get("languages", []) + facts.get("stack_hints", [])
            if str(x).strip()
        ]
        stack_ok = (not stack_terms) or any(term in lowered for term in stack_terms)

        contribution_terms = self._contribution_anchor_terms(facts)
        if not self._has_strong_contribution_signals(facts):
            contribution_ok = True
        else:
            contribution_ok = (not contribution_terms) or any(term in lowered for term in contribution_terms)
        return goal_ok, stack_ok, contribution_ok

    def _goal_anchor_matches(self, summary: str, goal_terms: list[str]) -> bool:
        """
        Return True when summary reflects at least one goal term with fuzzy matching.

        Goal phrases from README tags/themes are noisy and often paraphrased by ML.
        We accept exact phrase match or sufficient token overlap with normalized tokens.
        """
        lowered = str(summary or "").lower()
        summary_tokens = self._token_set(summary)
        if not summary_tokens:
            return False

        low_signal_goal_tokens = {
            "project", "goal", "goals", "outcome", "outcomes", "feature", "features",
            "app", "apps", "application", "applications", "workflow", "workflows",
            "service", "services", "system", "systems", "product", "products",
        }

        for raw_term in goal_terms:
            term = str(raw_term).strip().lower()
            if not term:
                continue

            # Keep exact phrase acceptance first for precision.
            if term in lowered:
                return True

            raw_tokens = self._token_set(term)
            if not raw_tokens:
                continue

            informative = {
                token for token in raw_tokens
                if len(token) >= 4 and token not in low_signal_goal_tokens
            }
            term_tokens = informative or raw_tokens

            overlap = term_tokens & summary_tokens
            if not overlap:
                continue

            # Accept if most informative tokens are present.
            coverage = len(overlap) / len(term_tokens)
            if coverage >= 0.5:
                return True

            # Multi-token phrases often get lightly paraphrased; 2 informative matches is enough.
            if len(term_tokens) >= 3 and len(overlap) >= 2:
                return True

            if len(term_tokens) == 1:
                return True

        return False

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

    def _has_strong_contribution_signals(self, facts: dict) -> bool:
        """
        Require contribution anchors only when contribution facts are strong.
        """
        if facts.get("role_description") or facts.get("role") or facts.get("commit_focus"):
            return True
        if isinstance(facts.get("commit_pct"), (int, float)) or isinstance(facts.get("line_pct"), (int, float)):
            return True
        activity = facts.get("activity_breakdown", []) or []
        if not activity:
            return False
        return not self._is_docs_only_activity(activity)

    def _is_docs_only_activity(self, activity_breakdown: list[tuple[str, float]]) -> bool:
        """
        Treat mostly-documentation activity as sparse contribution signals.
        """
        doc_tokens = {"documentation", "docs", "readme", "doc"}
        non_doc_pct = 0.0
        for domain, pct in activity_breakdown:
            tokens = self._token_set(str(domain))
            is_doc = bool(tokens & doc_tokens)
            if not is_doc:
                try:
                    non_doc_pct += float(pct)
                except (TypeError, ValueError):
                    non_doc_pct += 0.0
        return non_doc_pct <= 20.0

    def _compose_contribution_sentence(
        self,
        role: str | None,
        commit_focus: str | None,
        commit_pct: float | None,
        line_pct: float | None,
        activity_breakdown: list[tuple[str, float]] | None,
        allow_percentages: bool = False,
    ) -> str:
        """
        Compose a readable contribution sentence from available contribution metrics.
        """
        lead = "I contributed"
        role_text = str(role).replace("_", " ").strip() if role else None
        if role_text:
            lead += f" as a {role_text}"

        detail_phrases: list[str] = []
        if allow_percentages and isinstance(commit_pct, (int, float)):
            detail_phrases.append(f"authoring about {commit_pct:.0f}% of commits")
        elif allow_percentages and isinstance(line_pct, (int, float)):
            detail_phrases.append(f"accounting for about {line_pct:.0f}% of authored lines")

        if commit_focus:
            focus = str(commit_focus).replace("_", " ").strip().lower()
            detail_phrases.append(f"focusing on {focus} changes")

        activity_phrase = self._activity_phrase(activity_breakdown or [], allow_percentages=allow_percentages)
        if activity_phrase:
            detail_phrases.append(activity_phrase)

        if detail_phrases:
            return f"{lead}, {self._join_english(detail_phrases)}."
        return f"{lead} across project delivery tasks."

    def _activity_phrase(self, activity_breakdown: list[tuple[str, float]], *, allow_percentages: bool = False) -> str | None:
        """Return concise, professional activity-distribution wording."""
        if not activity_breakdown:
            return None

        top = activity_breakdown[:2]
        if not allow_percentages:
            if len(top) == 1:
                return f"primarily through {top[0][0]} work"
            return f"primarily through {top[0][0]} and {top[1][0]} work"
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

    def _token_set(self, text: str | None) -> set[str]:
        source = str(text or "")
        return set(
            normalized
            for t in re.findall(r"[a-z0-9]+", source.lower())
            if (normalized := self._normalize_token(t))
        )

    def _normalize_token(self, token: str) -> str:
        """Normalize tokens for forgiving lexical matching (simple singularization)."""
        cleaned = "".join(ch for ch in token.lower() if ch.isalnum())
        if not cleaned:
            return ""
        if cleaned.endswith("ies") and len(cleaned) > 4:
            return cleaned[:-3] + "y"
        if cleaned.endswith("es") and len(cleaned) > 4:
            return cleaned[:-2]
        if cleaned.endswith("s") and len(cleaned) > 3:
            return cleaned[:-1]
        return cleaned

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
            tags = pr.get_value(ProjectStatCollection.PROJECT_TAGS.value) or []
            tags = self._augment_tags(pr, tags)
            if not tags:
                continue
            lines.append(f"{pr.project_name}: {', '.join(tags)}")

        return lines

    def _augment_tags(self, project_report, tags: list[str]) -> list[str]:
        """Augment README tags with high-signal framework/feature hints."""
        merged: list[str] = []
        seen: set[str] = set()

        def _push(value: str):
            label = str(value or "").strip()
            if not label:
                return
            key = label.lower()
            if key in seen:
                return
            seen.add(key)
            merged.append(label)

        for tag in tags:
            _push(tag)

        frameworks = project_report.get_value(ProjectStatCollection.PROJECT_FRAMEWORKS.value) or []
        for ws in frameworks:
            name = str(getattr(ws, "skill_name", ws)).strip()
            if len(name) >= 2:
                _push(name)

        # Infer feature tags from common app/activity file names.
        for fr in getattr(project_report, "file_reports", []) or []:
            path = str(getattr(fr, "filepath", "") or "").lower()
            if "trip" in path:
                _push("Trip Creation")
            if "itinerary" in path:
                _push("Itinerary")
            if "event" in path:
                _push("Event Search")
            if "admin" in path:
                _push("Admin Panel")
            if "student" in path:
                _push("Student Records")
            if "course" in path:
                _push("Course Management")

        return merged[:20]


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
            themes = pr.get_value(ProjectStatCollection.PROJECT_THEMES.value) or []
            themes = self._augment_themes(pr, themes)
            if not themes:
                continue
            lines.append(f"{pr.project_name}: {', '.join(themes)}")

        return lines

    def _augment_themes(self, project_report, themes: list[str]) -> list[str]:
        """Augment themes with domain-first terms inferred from tags and file paths."""
        merged: list[str] = []
        seen: set[str] = set()

        def _push(value: str):
            label = str(value or "").strip()
            if not label:
                return
            key = label.lower()
            if key in seen:
                return
            seen.add(key)
            merged.append(label)

        for theme in themes:
            _push(theme)

        tags = project_report.get_value(ProjectStatCollection.PROJECT_TAGS.value) or []
        for tag in tags:
            term = str(tag).strip()
            if not term:
                continue
            # Prefer concise domain phrases as themes.
            if len(term.split()) <= 4 and not re.search(r"\.(sh|ps1|yml|yaml|txt)$", term.lower()):
                _push(term)

        for fr in getattr(project_report, "file_reports", []) or []:
            path = str(getattr(fr, "filepath", "") or "").lower()
            if "student" in path or "course" in path:
                _push("Student records and course management")
                break

        return merged[:10]


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
