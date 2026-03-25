import re

from src.core.report import UserReport
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextListBlock, TextBlock
from src.core.portfolio.builder.build_system import PortfolioSectionBuilder
from src.utils.data_processing import fmt_mdy, join_english
from src.core.statistic import ProjectStatCollection, UserStatCollection
from src.core.statistic.skills import SkillMapper
from src.core.ML.models.contribution_analysis import (
    generate_signature,
    build_signature_facts,
    resolve_experience_stage_with_ml,
)
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


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
        project_count = len(getattr(report, "project_reports", []) or [])
        if project_count <= 2 and experience_stage == "experienced":
            experience_stage = "early-career"
        project_names = [pr.project_name for pr in report.project_reports if getattr(
            pr, "project_name", None)]

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
        if signature and self._is_valid_summary(signature):
            return signature
        if signature:
            logger.warning(
                "Summary rejected by validator (len=%d, sentences=%d): %s",
                len(signature.split()),
                signature.count("."),
                signature[:200],
            )

        fallback = self._build_deterministic_summary(facts)
        if fallback:
            logger.info("Summary generated from builder-level deterministic fallback")
            return fallback
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
            cadence_counts[cadence_key] = cadence_counts.get(
                cadence_key, 0) + 1
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
            frameworks = pr.get_value(
                ProjectStatCollection.PROJECT_FRAMEWORKS.value)
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
            project_themes = pr.get_value(
                ProjectStatCollection.PROJECT_THEMES.value)
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
            project_tags = pr.get_value(
                ProjectStatCollection.PROJECT_TAGS.value)
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
            activity = pr.get_value(
                ProjectStatCollection.ACTIVITY_METRICS.value)
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
        corpus = " ".join(str(x) for x in (
            top_skills + tools + themes + tags) if x).lower()
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

    def _build_deterministic_summary(self, facts: dict) -> str | None:
        """
        Last-resort deterministic summary used when ML generation is unavailable
        or has failed validation. Builds a 2-3 sentence factual description from
        the signals already present in the facts payload.
        """
        top_skills = facts.get("top_skills") or []
        top_languages = facts.get("top_languages") or []
        tools = facts.get("tools") or []
        role = facts.get("role") or "contributor"
        focus = facts.get("focus")
        activities = facts.get("activities") or []

        if not top_skills and not top_languages and not tools:
            return None

        role_label = role.replace("_", " ").replace("-", " ").lower()
        if top_languages:
            sentence1 = (
                f"I am a software {role_label} with hands-on experience in "
                f"{join_english(top_languages[:2])}."
            )
        else:
            sentence1 = f"I am a software {role_label}."

        anchor_terms = (top_skills[:2] + tools[:1]) or tools[:3]
        if anchor_terms:
            sentence2 = f"My work spans {join_english(anchor_terms[:3])}."
        elif focus:
            sentence2 = f"My primary focus is {focus}."
        else:
            return None

        sentence3 = None
        if activities:
            sentence3 = f"I consistently deliver through {activities[0]}."
        elif focus:
            sentence3 = f"I focus on building {focus} solutions."

        parts = [sentence1, sentence2]
        if sentence3:
            parts.append(sentence3)
        return " ".join(parts)

    def _is_valid_summary(self, summary: str) -> bool:
        """Builder-level safety check before rendering summary block."""
        word_count = len(summary.split())
        sentence_count = summary.count(".")
        if word_count < 20 or word_count > 140:
            return False
        return 1 <= sentence_count <= 6

