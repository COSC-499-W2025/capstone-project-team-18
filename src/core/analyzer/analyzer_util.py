"""
This file holds top level functions for interacting
with the analyzer class structure.
"""

from multiprocessing import Pool, cpu_count
from git import Repo
from typing import Optional
from pathlib import Path

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
from src.database.api.models import UserConfigModel as UserConfig

logger = get_logger(__name__)


def single_file_analysis(
    args
) -> Optional[FileReport]:
    """
    Method to anlayze a single file. Grabs appropriate analyzer, checks if it should be included
    only as `INFO_FILE` and returns the analyzed fileReport.
    """
    (
        root_path,
        file,
        repo_path,
        email,
        github,
        language_filter,
        project_name,
    ) = args

    analyzer = get_appropriate_analyzer(
        root_path,
        str(file),
        Repo(repo_path) or None,
        email,
        github,
        language_filter,
    )

    if not analyzer.should_analyze_file():
        if analyzer.is_info_file():
            return analyzer.create_info_file()
        logger.info("Skipping file %s in project %s", file, project_name)
        return None

    try:
        return analyzer.analyze()

    except Exception:
        logger.exception("Error analyzing file %s in %s", file, project_name)
        return None


def extract_file_reports(
    project_file: ProjectLayout,
    user_config: UserConfig
) -> list[FileReport]:
    """
    Method to extract individual `FileReports` within each project
    """

    if project_file is None:
        raise ValueError(
            "Invalid state. extract_file_reports was given a None project_file")

    # Given a single project for a user and the project's structure return a list with each fileReport
    project_files = project_file.file_paths

    workers = max(1, cpu_count() - 1)

    args = [
        (
            str(project_file.root_path),
            file,
            project_file.repo.working_tree_dir if project_file.repo else None,
            email,
            github,
            language_filter,
            project_file.name,
        )
        for file in project_files
    ]

    with Pool(processes=workers) as pool:
        results = pool.map(single_file_analysis, args)

    return [r for r in results if r is not None]


def get_appropriate_analyzer(user_config: UserConfig,
                             project_context: ProjectLayout,
                             relative_path: str
                             ) -> BaseFileAnalyzer:
    """
    Factory function to return the most appropriate analyzer for a given file.
    This allows `FileReport` to automatically use the best analyzer.
    """

    file_path = project_context.root_path / Path(relative_path)
    extension = file_path.suffix.lower()

    if file_path.is_dir():
        raise ValueError(
            f"Cannot analyze a directory: {file_path}. Must be a file.")

    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist.")

    # Natural language files
    natural_language_extensions = {'.md', '.txt', '.rst', '.doc', '.docx'}
    if extension in natural_language_extensions:
        return NaturalLanguageAnalyzer(user_config, project_context, relative_path)

    # Python files
    if extension == '.py':
        return PythonAnalyzer(user_config, project_context, relative_path)
    # Java files
    if extension == '.java':
        return JavaAnalyzer(user_config, project_context, relative_path)

    # JavaScript files
    if extension in {'.js', '.jsx'}:
        return JavaScriptAnalyzer(user_config, project_context, relative_path)
    # C files
    if extension == '.c':
        return CAnalyzer(user_config, project_context, relative_path)

    # TypeScript files
    if extension in {'.ts', '.tsx'}:
        return TypeScriptAnalyzer(user_config, project_context, relative_path)
    # CSS files
    if extension == '.css':
        return CSSAnalyzer(user_config, project_context, relative_path)

    # HTML or HTM files
    if extension in {'.html', '.htm'}:
        return HTMLAnalyzer(user_config, project_context, relative_path)
    # PHP files
    if extension == '.php':
        return PHPAnalyzer(user_config, project_context, relative_path)

    # Text-based files
    text_extensions = {'.xml', '.json', '.yml', '.yaml'}
    if extension in text_extensions:
        return TextFileAnalyzer(user_config, project_context, relative_path)

    for language, lang_extensions in LANGUAGE_EXTENSIONS.items():
        if extension in lang_extensions:
            return CodeFileAnalyzer(user_config, project_context, relative_path)

    # Default to base analyzer
    return BaseFileAnalyzer(user_config, project_context, relative_path)
