import zipfile
from pathlib import Path
from typing import Dict, List, Set, Optional
import logging
import tempfile
import shutil
from git import Repo, InvalidGitRepositoryError

logger = logging.getLogger(__name__)


def discover_projects(zip_path: str) -> Dict[str, List[str]]:
    """Returns dict mapping project names to their file paths from a zip file."""
    if not Path(zip_path).exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    projects = {}
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for path in zf.namelist():
                # Skip directory entries
                if path.endswith('/'):
                    continue

                parts = Path(path).parts
                if not parts:
                    continue

                # First part is project name, rest is file path
                name = parts[0]
                file = str(Path(*parts[1:])) if len(parts) > 1 else parts[0]

                projects.setdefault(name, []).append(file)

    except zipfile.BadZipFile as e:
        logger.error(f"Invalid zip file: {zip_path}. Error: {str(e)}")
        raise

    return projects


def is_group_project(zip_path: str, project_name: str) -> Optional[str]:
    """Returns 'individual', 'group', or None based on Git commit authors."""
    if not Path(zip_path).exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    temp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Extract only files belonging to this project
            files = [f for f in zf.namelist()
                     if f.startswith(f"{project_name}/")]

            if not files:
                return None

            for path in files:
                zf.extract(path, temp)

        try:
            repo = Repo(Path(temp) / project_name)
            # Count unique commit authors by email
            authors = {c.author.email for c in repo.iter_commits()}
            return "individual" if len(authors) == 1 else "group" if authors else None
        except InvalidGitRepositoryError:
            return None

    except zipfile.BadZipFile as e:
        logger.error(f"Invalid zip file: {zip_path}. Error: {str(e)}")
        raise
    finally:
        shutil.rmtree(temp, ignore_errors=True)
