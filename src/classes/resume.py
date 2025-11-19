"""
This class holds all the logic
for building and managing resumes.
"""

from dataclasses import dataclass
from datetime import date
from .statistic import ProjectStatCollection, WeightedSkills, CodingLanguage


@dataclass
class ResumeItem:
    """
    A single item for paragraph in resume. It is
    a single project
    """

    title: str
    bullet_points: list[str]
    start_date: date
    end_date: date


class Resume:
    """
    This is the main resume class that holds all the
    resume items and can generate a formatted resume.

    Attributes:
        items (list[ResumeItem]): A list of resume items.
        skills (list[str]): A list of skills.

    """

    # TODO: Expand more attributes like contact info, summary, etc.

    def __init__(self):
        self.items = []
        self.skills = []

    def add_item(self, item: ResumeItem):
        self.items.append(item)

    def add_skill(self, skill: str):
        self.skills.append(skill)

    def generate_resume(self) -> str:
        resume = ""
        for item in self.items:
            resume += f"{item.title} : {item.start_date} - {item.end_date}\n"
            for bullet in item.bullet_points:
                resume += f"   - {bullet}\n"
            resume += "\n"
        return resume

    def __str__(self) -> str:
        return self.generate_resume()


def bullet_point_builder(project_report: "ProjectReport") -> list[str]:
    """
    This function intakes a project report and analyzes
    the report's statistics to build bullet points for
    a resume item.

    We do not assume anything special about the project
    report expect that it has the base information (Project
    name, start date, and end date). Any other statistics
    are optional and will be used if available.

    This function is reslient and will not throw errors. You are
    guarrenteed to get at least one bullet point back.

    Args:
        project_report (ProjectReport): The project report to analyze.

    Returns:
        list[str]: A list of bullet points for the resume item.
    """

    bullet_points = []

    # 1) Coding language breakdown
    lang_ratio = project_report.get_value(
        ProjectStatCollection.CODING_LANGUAGE_RATIO.value)

    if lang_ratio:
        bullet_points.append(coding_language_bp(lang_ratio))

    # 2) Skills demonstrated (take top 3 by weight)
    skills = project_report.get_value(
        ProjectStatCollection.PROJECT_SKILLS_DEMONSTRATED.value)

    if skills:
        bullet_points.append(weight_skills_bp(skills))

    # 3) Authorship / collaboration
    is_group = project_report.get_value(
        ProjectStatCollection.IS_GROUP_PROJECT.value)
    total_authors = project_report.get_value(
        ProjectStatCollection.TOTAL_AUTHORS.value)

    if is_group:
        if total_authors:
            bullet_points.append(
                f"Collaborated in a team of {total_authors - 1} contributors")
        else:
            bullet_points.append("Collaborated with multiple contributors")
    else:
        if is_group is False:
            bullet_points.append(
                "I individually designed, developed, and led the project")

    # 4) Commit percentage (if available)
    user_commit_pct = project_report.get_value(
        ProjectStatCollection.USER_COMMIT_PERCENTAGE.value)

    if user_commit_pct is not None:
        bullet_points.append(f"Authored {user_commit_pct}% of commits")

    # 5) Contribution percentage (if available)
    total_contrib_pct = project_report.get_value(
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)

    if total_contrib_pct is not None:
        bullet_points.append(
            f"Accounted for {total_contrib_pct}% of total contribution")

    # Ensure at least one bullet exists
    if len(bullet_points) == 0:
        bullet_points.append(
            f"I contributued and worked on the project {project_report.project_name}")

    return bullet_points


def coding_language_bp(coding_language_ratio: dict[CodingLanguage, float]) -> str:
    """
    This function generates a bullet point
    for coding languages used in the project.
    We assume that anything more than (10%) of the code
    is worth mentioning in the resume.

    Will return None if no coding language data is available.

    Args:
        project_report (ProjectReport): The project report to analyze.

    Returns:
        str: A bullet point for the resume item.
    """

    # Consider only languages with at least 10% usage
    lang_ratio: dict[CodingLanguage, float] = {
        lang: frac for lang, frac in coding_language_ratio.items() if frac >= 0.1}

    if len(lang_ratio) == 0:
        return "Implemented code in small amounts of many programming languages"

    # If only one language, return
    if len(lang_ratio) == 1:
        for lang in lang_ratio.keys():
            name = lang.value[0]
            return f"Project was coded using the {name} language"

    # Multiple languages, get top and others
    top_lang = max(lang_ratio.items(), key=lambda kv: kv[1])[0]
    other_langs = [lang for lang in lang_ratio.keys()
                   if lang != top_lang]

    top_name = top_lang.value[0]
    other_names = [lang.value[0] for lang in other_langs]

    return f"Implemented code mainly in {top_name} and also in {', '.join(other_names)}"


def weight_skills_bp(weighted_skills: list[WeightedSkills]) -> str:
    """
    This function generates a bullet point
    for weighted skills demonstrated in the project.
    We take the top 3 weighted skills and list them.

    Args:
        weighted_skills (list[WeightedSkills]): List of WeightedSkills objects.

    Returns:
        str: A bullet point for the resume item.
    """

    sorted_skills = sorted(weighted_skills, key=lambda s: getattr(
        s, 'weight', 0), reverse=True)

    top = sorted_skills[:3]

    return f"Utilized skills {', '.join([s.skill_name for s in top])}"
