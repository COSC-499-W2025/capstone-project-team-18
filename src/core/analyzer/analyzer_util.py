"""
This file holds top level functions for interacting
with the analyzer class structure.
"""

from git import Repo
from pathlib import Path
from typing import Optional

from src.core.report.file_report import FileReport
from src.core.statistic import LANGUAGE_EXTENSIONS
from src.core.project_discovery.project_discovery import ProjectLayout
from src.core.analyzer.base_file_analyzer import BaseFileAnalyzer
from src.core.analyzer.c_analyzer import CAnalyzer
from src.core.analyzer.code_file_analyzer import CodeFileAnalyzer
from src.core.analyzer.css_analyzer import CSSAnalyzer
from src.core.analyzer.html_analyzer import HTMLAnalyzer
from src.core.analyzer.java_analyzer import JavaAnalyzer
from src.core.analyzer.java_script_analyzer import JavaScriptAnalyzer
from src.core.analyzer.natural_language_analyzer import NaturalLanguageAnalyzer
from src.core.analyzer.php_analyzer import PHPAnalyzer
from src.core.analyzer.python_analyzer import PythonAnalyzer
from src.core.analyzer.text_file_analyzer import TextFileAnalyzer
from src.core.analyzer.type_script_analyzer import TypeScriptAnalyzer
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def extract_file_reports(
    project_file: ProjectLayout,
    email: Optional[str] = None,
    github: Optional[str] = None,
    language_filter: Optional[list[str]] = None
) -> list[FileReport]:
    """
    Method to extract individual `FileReports` within each project
    """

    if project_file is None:
        raise ValueError(
            "Invalid state. extract_file_reports was given a None project_file")

    # Given a single project for a user and the project's structure return a list with each fileReport
    project_files = project_file.file_paths

    # list of reports for each file in an individual project to be returned
    reports = []
    for file in project_files:

        analyzer = get_appropriate_analyzer(
            str(project_file.root_path),
            str(file),
            project_file.repo,
            email,
            github,
            language_filter)

        if analyzer.should_include() is False:
            reports.append(analyzer.is_info_file())
            logger.info("Skipping file %s in project %s",
                        file, project_file.name)
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
    github: Optional[str] = None,
    language_filter: Optional[list[str]] = None
) -> BaseFileAnalyzer:
    """
    Factory function to return the most appropriate analyzer for a given file.
    This allows `FileReport` to automatically use the best analyzer.
    """

    file_path = Path(path_to_top_level_project + "/" + relative_path)
    extension = file_path.suffix.lower()

    if file_path.is_dir():
        raise ValueError(
            f"Cannot analyze a directory: {file_path}. Must be a file.")

    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist.")

    # Natural language files
    natural_language_extensions = {'.md', '.txt', '.rst', '.doc', '.docx'}
    if extension in natural_language_extensions:
        return NaturalLanguageAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)

    # Python files
    if extension == '.py':
        return PythonAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)
    # Java files
    if extension == '.java':
        return JavaAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)

    # JavaScript files
    if extension in {'.js', '.jsx'}:
        return JavaScriptAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)
    # C files
    if extension == '.c':
        return CAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)

    # TypeScript files
    if extension in {'.ts', '.tsx'}:
        return TypeScriptAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)
    # CSS files
    if extension == '.css':
        return CSSAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)

    # HTML or HTM files
    if extension in {'.html', '.htm'}:
        return HTMLAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)
    # PHP files
    if extension == '.php':
        return PHPAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)

    # Text-based files
    text_extensions = {'.xml', '.json', '.yml', '.yaml'}
    if extension in text_extensions:
        return TextFileAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)

    for language, lang_extensions in LANGUAGE_EXTENSIONS.items():
        if extension in lang_extensions:
            return CodeFileAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)

    # Default to base analyzer
    return BaseFileAnalyzer(path_to_top_level_project, relative_path, repo, email, github, language_filter)
