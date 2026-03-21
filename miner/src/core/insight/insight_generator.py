"""
Generates human-readable project insights from an existing ProjectReport.

Insights are prompts designed to help a user reflect on their contributions
when editing their resume. They are derived at request time from already-mined
statistics — no new mining or database writes are needed.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Type
from abc import ABC, abstractmethod

from src.core.statistic.project_stat_collection import ProjectStatCollection
from src.infrastructure.log.logging import get_logger
from src.core.statistic.statistic_models import FileDomain, WeightedSkills

logger = get_logger(__name__)

if TYPE_CHECKING:
    from src.core.report.project.project_report import ProjectReport


@dataclass
class ProjectInsight:
    message: str


class InsightCalculator(ABC):
    @abstractmethod
    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        """
        Calculate ProjectInsights
        """
        raise NotImplementedError(
            "Subclasses must implement the calculate method.")


def _join_terms(items: list[str], limit: int = 3) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    top = cleaned[:limit]
    if not top:
        return ""
    if len(top) == 1:
        return top[0]
    if len(top) == 2:
        return f"{top[0]} and {top[1]}"
    return f"{top[0]}, {top[1]}, and {top[2]}"


class ActivityInsightCalculator(InsightCalculator):
    """Highlights file domains where the user made notable contributions."""

    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        contributions = report.get_value(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value
        )
        if not contributions:
            return []

        insights: list[ProjectInsight] = []

        # Normalise keys: FileDomain enum instances or raw strings from DB
        normalised: dict[str, float] = {}
        for key, val in contributions.items():
            if isinstance(key, FileDomain):
                normalised[key.value] = val
            else:
                normalised[str(key)] = val

        code_pct = normalised.get(FileDomain.CODE.value, 0.0)
        test_pct = normalised.get(FileDomain.TEST.value, 0.0)
        design_pct = normalised.get(FileDomain.DESIGN.value, 0.0)
        doc_pct = normalised.get(FileDomain.DOCUMENTATION.value, 0.0)

        if code_pct >= 50.0:
            insights.append(ProjectInsight(
                message=(
                    f"You contributed {round(code_pct)}% of your work to code files in this project. "
                    "What specific features or systems did you build?"
                ),
            ))
        elif code_pct >= 30.0:
            insights.append(ProjectInsight(
                message=(
                    "You made solid code contributions here. "
                    "Can you describe a specific feature or component you implemented?"
                ),
            ))

        if test_pct >= 25.0:
            insights.append(ProjectInsight(
                message=(
                    f"About {round(test_pct)}% of your contributions were to test files. "
                    "What testing strategies or frameworks did you use, and how did they improve quality?"
                ),
            ))

        if design_pct >= 20.0:
            insights.append(ProjectInsight(
                message=(
                    "You contributed to design files in this project. "
                    "What UI/UX decisions or visual components did you work on?"
                ),
            ))

        if doc_pct >= 20.0:
            insights.append(ProjectInsight(
                message=(
                    "You wrote a significant amount of documentation. "
                    "What key aspects of the project did you document, and why was that important?"
                ),
            ))

        return insights


class OwnershipInsightCalculator(InsightCalculator):
    """Prompts based on how much of the project the user owns."""

    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        commit_pct = report.get_value(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value
        )
        line_pct = report.get_value(
            ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value
        )
        group_project = report.get_value(
            ProjectStatCollection.IS_GROUP_PROJECT.value
        )

        if group_project is None or not group_project:
            return []

        insights: list[ProjectInsight] = []

        # Use whichever metric is available; prefer commit percentage
        ownership = commit_pct if commit_pct is not None else line_pct
        if ownership is None:
            return []

        if ownership >= 70.0:
            insights.append(ProjectInsight(
                message=(
                    f"You authored roughly {round(ownership)}% of this project — "
                    "you were clearly the primary contributor. "
                    "What were the biggest technical challenges you tackled alone?"
                ),
            ))
        elif ownership >= 40.0:
            insights.append(ProjectInsight(
                message=(
                    f"You contributed about {round(ownership)}% of this project. "
                    "What were your main responsibilities, and how did they fit into the bigger picture?"
                ),
            ))

        return insights


class CollaborationInsightCalculator(InsightCalculator):
    """Prompts about team dynamics and the user's role."""

    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        is_group = report.get_value(
            ProjectStatCollection.IS_GROUP_PROJECT.value)
        total_authors = report.get_value(
            ProjectStatCollection.TOTAL_AUTHORS.value)
        role = report.get_value(ProjectStatCollection.COLLABORATION_ROLE.value)
        role_desc = report.get_value(
            ProjectStatCollection.ROLE_DESCRIPTION.value)

        insights: list[ProjectInsight] = []

        if is_group and total_authors and total_authors > 1:
            insights.append(ProjectInsight(
                message=(
                    f"This was a team project with {total_authors} contributors. "
                    "How did you coordinate with your teammates, and what was your specific area of ownership?"
                ),
            ))

        if role:
            role_lower = role.lower()
            if any(kw in role_lower for kw in ("lead", "senior", "architect", "owner")):
                insights.append(ProjectInsight(
                    message=(
                        f"Your inferred role was '{role}'. "
                        "Did you make key architectural decisions or mentor other contributors? "
                        "Describing that on a resume can set you apart."
                    ),
                ))
            elif role_desc:
                insights.append(ProjectInsight(
                    message=(
                        f"Based on your commit history, your role was: \"{role_desc}\" "
                        "Can you give a concrete example of something you delivered in that capacity?"
                    ),
                ))
        else:
            if role_desc:
                insights.append(ProjectInsight(
                    message=(
                        f"Your contribution pattern suggests this role: \"{role_desc}\" "
                        "What concrete outcome or deliverable best demonstrates that impact on your resume?"
                    ),
                ))

        return insights


class SkillsInsightCalculator(InsightCalculator):
    """Prompts the user to talk about the top technologies they used."""

    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        skills = report.get_value(
            ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value
        )
        frameworks = report.get_value(
            ProjectStatCollection.PROJECT_FRAMEWORKS.value
        )

        # Merge skills and frameworks, prefer skills if both present
        combined: list[WeightedSkills] = []
        for source in (skills, frameworks):
            if source:
                for item in source:
                    if isinstance(item, WeightedSkills):
                        combined.append(item)
                    elif isinstance(item, dict):
                        name = item.get("skill_name") or item.get("name")
                        weight = item.get("weight", 0.0)
                        if name:
                            combined.append(WeightedSkills(
                                skill_name=name, weight=weight))

        if not combined:
            return []

        combined.sort(reverse=True)
        top = [ws.skill_name for ws in combined[:3] if ws.skill_name]

        if not top:
            return []

        skills_str = _join_terms(top)

        return [ProjectInsight(
            message=(
                f"You used {skills_str} in this project. "
                "How did these technologies help you solve a specific problem? "
                "Concrete examples make resume bullet points much stronger."
            ),
        )]


class ReadmeNarrativeInsightCalculator(InsightCalculator):
    """Prompts the user to translate README-level ML signals into resume language."""

    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        themes = report.get_value(ProjectStatCollection.PROJECT_THEMES.value) or []
        tags = report.get_value(ProjectStatCollection.PROJECT_TAGS.value) or []
        tone = report.get_value(ProjectStatCollection.PROJECT_TONE.value)

        insights: list[ProjectInsight] = []

        if themes:
            theme_text = _join_terms(themes, limit=2)
            insights.append(ProjectInsight(
                message=(
                    f"Your project narrative centers on {theme_text}. "
                    "How would you describe the problem space, the users served, and the outcome you delivered?"
                ),
            ))
        elif tags:
            tag_text = _join_terms(tags, limit=3)
            insights.append(ProjectInsight(
                message=(
                    f"Key project ideas inferred from the README include {tag_text}. "
                    "Which of those best reflects the project impact you want to emphasize on your resume?"
                ),
            ))

        if tone:
            insights.append(ProjectInsight(
                message=(
                    f"The README presents this work with a {tone.lower()} tone. "
                    "What evidence from the codebase or deliverables supports telling that story in a resume bullet?"
                ),
            ))

        return insights


class CommitFocusInsightCalculator(InsightCalculator):
    """Prompts based on the dominant ML-inferred commit focus for the project."""

    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        distribution = report.get_value(
            ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value
        )
        if not distribution:
            return []

        ranked = sorted(
            ((str(label).strip().lower(), float(weight)) for label, weight in distribution.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        if not ranked:
            return []

        top_label, top_weight = ranked[0]
        if not top_label or top_weight <= 0:
            return []

        if top_label in {"feature", "features"}:
            message = (
                f"About {round(top_weight)}% of your commits were feature-focused. "
                "Which end-user capability or product improvement best captures that delivery work on your resume?"
            )
        elif top_label in {"fix", "bugfix", "bug", "bugs"}:
            message = (
                f"A large share of your commits ({round(top_weight)}%) were focused on fixes. "
                "What reliability, stability, or production issue did you resolve that is worth highlighting?"
            )
        elif top_label in {"refactor", "cleanup", "maintenance"}:
            message = (
                f"Roughly {round(top_weight)}% of your commits were refactoring-oriented. "
                "What did you improve in the system design, maintainability, or code quality that would strengthen a resume bullet?"
            )
        elif top_label in {"docs", "documentation"}:
            message = (
                f"Documentation-related commits made up about {round(top_weight)}% of your work. "
                "What important documentation, onboarding material, or technical communication did you own?"
            )
        elif top_label in {"test", "tests", "testing", "qa"}:
            message = (
                f"Testing-focused work accounted for about {round(top_weight)}% of your commits. "
                "What test coverage or quality improvements did you deliver that are worth calling out?"
            )
        else:
            message = (
                f"Your dominant commit focus was '{top_label}' at about {round(top_weight)}% of commits. "
                "What concrete accomplishment best represents that pattern of work on your resume?"
            )

        return [ProjectInsight(message=message)]


class WorkPatternInsightCalculator(InsightCalculator):
    """Prompts based on detected work cadence."""

    def calculate(self, report: "ProjectReport") -> list[ProjectInsight]:
        pattern = report.get_value(ProjectStatCollection.WORK_PATTERN.value)
        if not pattern:
            return []

        pattern_lower = pattern.lower()

        if "sprint" in pattern_lower:
            return [ProjectInsight(
                message=(
                    "Your commit history shows a sprint-based work style. "
                    "Can you describe a sprint goal you drove and how your team delivered it?"
                ),
            )]
        if "burst" in pattern_lower:
            return [ProjectInsight(
                message=(
                    "You had intense bursts of activity on this project. "
                    "What drove those periods — a deadline, a specific feature push, or something else?"
                ),
            )]
        if "consistent" in pattern_lower:
            return [ProjectInsight(
                message=(
                    "Your contributions were steady and consistent throughout the project. "
                    "What practices helped you maintain that momentum?"
                ),
            )]

        return []


class InsightGenerator:
    """
    Derives a list of ProjectInsight objects from a ProjectReport.

    Dynamically loads and executes InsightCalculators to generate insights.
    """

    # Register all calculators here
    master_list: list[Type[InsightCalculator]] = [
        ActivityInsightCalculator,
        OwnershipInsightCalculator,
        CollaborationInsightCalculator,
        SkillsInsightCalculator,
        ReadmeNarrativeInsightCalculator,
        CommitFocusInsightCalculator,
        WorkPatternInsightCalculator,
    ]

    @classmethod
    def generate(cls, report: "ProjectReport", requested_classes: Optional[List[Type[InsightCalculator]]] = None) -> list[ProjectInsight]:
        calculators: list[InsightCalculator] = []

        if requested_classes is not None:
            if len(requested_classes) == 0:
                logger.warning(
                    f"{cls.__name__} called with no requested calculators.")
            else:
                calculators = [
                    calc_cls() for calc_cls in cls.master_list
                    if calc_cls in requested_classes
                ]
        else:
            # Default to all available calculators
            calculators = [calc_cls() for calc_cls in cls.master_list]

        all_insights: list[ProjectInsight] = []

        for calc in calculators:
            # Calculate returns a list of insights
            generated_insights = calc.calculate(report)
            if generated_insights:
                all_insights.extend(generated_insights)

        return all_insights
