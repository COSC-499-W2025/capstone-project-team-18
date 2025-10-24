import zipfile
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def discover_projects(zip_path: str) -> Dict[str, List[str]]:
    """Returns dictionary mapping project names to their file paths from a zip file."""
    if not Path(zip_path).exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    projects = {}
    all_files = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for path in zf.namelist():
                # Skip directory entries and Mac metadata
                if path.endswith('/') or '__MACOSX' in path or path.endswith('.DS_Store'):
                    continue
                all_files.append(path)

            if not all_files:
                return projects

            # Group files by their first directory level
            first_level = {}
            for path in all_files:
                parts = Path(path).parts
                if len(parts) > 0:
                    first_level.setdefault(parts[0], []).append(parts)

            # Check if all files share a common parent folder
            if len(first_level) == 1:
                # Single top-level folder
                parent = list(first_level.keys())[0]
                all_parts = first_level[parent]

                # Check if there are any files with second-level directories
                has_subdirs = any(len(p) > 2 for p in all_parts)

                if has_subdirs:
                    # Has subdirectories - skip parent, use second level as projects
                    second_level_dirs = {p[1] for p in all_parts if len(p) > 1}

                    # Only skip parent if ALL files have second-level dirs
                    all_have_second = all(len(p) > 1 for p in all_parts)

                    if all_have_second and len(second_level_dirs) > 1:
                        # Multiple second-level dirs - use them as project names
                        for path in all_files:
                            parts = Path(path).parts
                            if len(parts) >= 2:
                                name = parts[1]
                                file = str(
                                    Path(*parts[2:])) if len(parts) > 2 else parts[1]
                                projects.setdefault(name, []).append(file)
                    else:
                        # Use parent as project name
                        for path in all_files:
                            parts = Path(path).parts
                            name = parts[0]
                            file = str(
                                Path(*parts[1:])) if len(parts) > 1 else parts[0]
                            projects.setdefault(name, []).append(file)
                else:
                    # No subdirectories - use parent as project name
                    for path in all_files:
                        parts = Path(path).parts
                        name = parts[0]
                        file = str(Path(*parts[1:])
                                   ) if len(parts) > 1 else parts[0]
                        projects.setdefault(name, []).append(file)
            else:
                # Multiple top-level folders - use first level as project names
                for path in all_files:
                    parts = Path(path).parts
                    name = parts[0]
                    file = str(Path(*parts[1:])
                               ) if len(parts) > 1 else parts[0]
                    projects.setdefault(name, []).append(file)

    except zipfile.BadZipFile as e:
        logger.error(f"Invalid zip file: {zip_path}. Error: {str(e)}")
        raise

    return projects
