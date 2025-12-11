"""
This file holds top level functions for interacting
with the analyzer class structure.
"""

from git import Repo
from pathlib import Path
import logging
from typing import Optional

from src.classes.report.file_report import FileReport
from src.classes.statistic import CodingLanguage
from src.utils.project_discovery.project_discovery import ProjectFiles
from src.classes.analyzer.base_file_analyzer import BaseFileAnalyzer
from src.classes.analyzer.c_analyzer import CAnalyzer
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer
from src.classes.analyzer.css_analyzer import CSSAnalyzer
from src.classes.analyzer.html_analyzer import HTMLAnalyzer
from src.classes.analyzer.java_analyzer import JavaAnalyzer
from src.classes.analyzer.java_script_analyzer import JavaScriptAnalyzer
from src.classes.analyzer.natural_language_analyzer import NaturalLanguageAnalyzer
from src.classes.analyzer.php_analyzer import PHPAnalyzer
from src.classes.analyzer.python_analyzer import PythonAnalyzer
from src.classes.analyzer.text_file_analyzer import TextFileAnalyzer
from src.classes.analyzer.type_script_analyzer import TypeScriptAnalyzer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_file_reports(
    project_file: Optional[ProjectFiles],
    email: Optional[str] = None,
    language_filter: Optional[list[str]] = None
) -> list[FileReport]:
    """
    Method to extract individual `FileReports` within each project
    """

    if project_file is None:
        return []

    # Given a single project for a user and the project's structure return a list with each fileReport
    projectFiles = project_file.file_paths

    # list of reports for each file in an individual project to be returned
    reports = []
    for file in projectFiles:

        analyzer = get_appropriate_analyzer(
            project_file.root_path,
            file,
            project_file.repo,
            email,
            language_filter)

        if analyzer.should_include() is False:
            continue

        try:
            reports.append(analyzer.analyze())
        except Exception as e:
            logger.error(
                f"Error analyzing file {file} in {project_file.name}: {e}")

    return reports


def get_appropriate_analyzer(
    path_to_top_level_project: str,
    relative_path: str,
    repo: Optional[Repo] = None,
    email: Optional[str] = None,
    language_filter: Optional[list[str]] = None
) -> BaseFileAnalyzer:
    """
    Factory function to return the most appropriate analyzer for a given file.
    This allows `FileReport` to automatically use the best analyzer.
    """

    file_path = Path(path_to_top_level_project + "/" + relative_path)
    extension = file_path.suffix.lower()

    # Natural language files
    natural_language_extensions = {'.md', '.txt', '.rst', '.doc', '.docx'}
    if extension in natural_language_extensions:
        return NaturalLanguageAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)

    # Python files
    if extension == '.py':
        return PythonAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)
    # Java files
    if extension == '.java':
        return JavaAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)

    # JavaScript files
    if extension in {'.js', '.jsx'}:
        return JavaScriptAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)
    # C files
    if extension == '.c':
        return CAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)

    # TypeScript files
    if extension in {'.ts', '.tsx'}:
        return TypeScriptAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)
    # CSS files
    if extension == '.css':
        return CSSAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)

    # HTML or HTM files
    if extension in {'.html', '.htm'}:
        return HTMLAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)
    # PHP files
    if extension == '.php':
        return PHPAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)

    # Text-based files
    text_extensions = {'.xml', '.json', '.yml', '.yaml'}
    if extension in text_extensions:
        return TextFileAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)

    for language in CodingLanguage:
        if extension in language.value[1]:
            return CodeFileAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)

    # Default to base analyzer
    return BaseFileAnalyzer(path_to_top_level_project, relative_path, repo, email, language_filter)
