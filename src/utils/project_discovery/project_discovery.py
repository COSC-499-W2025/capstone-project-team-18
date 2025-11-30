"""
A file that handles logic for project discovery. Meaning, given
a zipped file, with directories are projects? Which files
should be considered?
"""

import os
from pathlib import Path
from dataclasses import dataclass
import logging
from typing import Optional
from git import Repo
from .ignore_constants import *

logger = logging.getLogger(__name__)


@dataclass
class ProjectFiles:
    name: str  # Name of the project (name of the top level directory)
    root_path: str  # The absolute path to the top-level directory
    file_paths: list[str]  # File paths relative to the root_path
    repo: Optional[Repo]  # The git repository object if applicable


def discover_projects(unzipped_dir: str) -> list[ProjectFiles]:
    """
    Given the path to the directory where the zip file was extracted,
    discover the projects and their files.

    The way we do this is:
    1. Look at each top-level directory (ignore files at the top level)
    2. For each top-level directory, check if it is a project using heuristics
         (see dir_is_project function).
    3. If it is a project, add it to the list of projects.
    4. If it is not a project, look at its subdirectories and repeat step 2-4.

    The assumption here is that projects are always in their own directories.

    Args:
        - unzipped_dir : str The path to the directory where the zip file was extracted

    Returns:
        - list[ProjectFiles] A list of ProjectFiles dataclasses representing the discovered projects.

    Raises:
        - FileNotFoundError: If the unzipped directory does not exist.

    """

    if not Path(unzipped_dir).exists():
        raise FileNotFoundError(f"Directory not found: {unzipped_dir}")

    # MACOSX specific handling: ignore __MACOSX folder
    top_level_folders = [f for f in Path(
        unzipped_dir).iterdir() if f.is_dir() and f.name != "__MACOSX"
    ]

    projects = []

    def process_directory(dir_path: Path) -> None:
        """
        Recursive helper function to process directories.
        """

        if dir_is_project(dir_path):

            file_paths = filter_files(dir_path)

            # Check to see if the project is a git repository
            repo = None
            try:
                repo = Repo(dir_path)
            except Exception as e:
                logger.debug(f"No git repository found in {dir_path}: {e}")

            projects.append(ProjectFiles(
                name=dir_path.name,
                root_path=str(dir_path),
                file_paths=file_paths,
                repo=repo
            ))

        else:
            # If the directory is not a project, it likely has projects in subdirectories
            # Check those and move on.
            for sub_dir in dir_path.iterdir():
                if sub_dir.is_dir():
                    process_directory(sub_dir)

    for top_level_dir in top_level_folders:
        process_directory(top_level_dir)

    return projects


def dir_is_project(dir_path: Path) -> bool:
    """
    Heuristics to determine if a directory is a project.

    Args:
        - dir_path : Path The path to the directory to check.

    Returns:
        - bool True if the directory is a project, False otherwise.
    """

    # Check for instant project directories
    for instant_dir in INSTANT_SUCCESS_FILES_AND_DIR:
        if (dir_path / instant_dir).exists():
            return True

    # Check if there are any files (excluding junk files)
    files = [f for f in dir_path.iterdir() if f.is_file()
             and f.name not in JUNK_FILES]

    if len(files) == 0:
        return False

    return True


def filter_files(project_path: Path) -> list[str]:
    """
    Given that we know a folder is a project,
    this function will filter all the files in
    the directory and return ONLY files that should
    be analyzed. It ignores files that we don't care
    about like '.gitignore' or anything in the
    .git directory.

    """

    # We ignore the ignore files and the files in the IGNORE_DIRS directories
    file_paths = []

    for root, dirs, files in os.walk(project_path):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file not in IGNORE_FILES:

                # Check if file has an ignored extension
                if not any(file.endswith(ext) for ext in IGNORE_EXTENSIONS):
                    full_path = Path(root) / file
                    relative_path = full_path.relative_to(project_path)
                    file_paths.append(str(relative_path))

    return file_paths
