"""
This file will run everytime pytest
starts running tests. It is used to
make global changes to the testing environment.
"""

import sys
from pathlib import Path
import pytest
from git import Repo
from src.utils.project_discovery.project_discovery import ProjectFiles

"""
When pytest runs, we consider capstone-project-team-18
to be the root of the project for imports.

However, when we run the application normally,
the src/ directory is considered to be the root
for imports.

This makes us run in to error in a situation
like this:

- pytest imports ArtifactMiner with:
    from src.classes.cli import ArtifactMiner

- but ArtifactMiner tries to import start_miner with:
    from app import start_miner

Error can't find app!

So here, we adjust sys.path to ensure that
imports work correctly in both scenarios.
"""
# Repository root (this file is at the repo root)
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"

# Ensure the repository root is on sys.path so imports like `import src...`
# resolve consistently when pytest runs from the project root.
sys.path.insert(0, str(REPO_ROOT))

# Also ensure the src/ directory itself is on sys.path. This helps in cases
# where code or tests expect modules to be importable directly from src.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# --- Helper Functions --


def _create_temp_file(filename: str, content: str, path: Path, encoding: str = "utf-8") -> list[str]:
    """
    Helper function to create a new file with
    the provided name, in the provided path,
    with the provided content in the provided encoding.
    """

    path_full = path / filename
    path_full.write_text(content, encoding=encoding)
    return [str(path), filename]


# --- Fixtures --
# These are global objects that we can use in our test

RESOURCE_DIR = Path(__file__).parent / "tests/resources"


@pytest.fixture
def temp_text_file(tmp_path: Path) -> list[str]:
    """
    Creates a temporary text file.

    Returns:
        list[str] : [tmp_path, "sample.txt"]
    """

    return _create_temp_file("sample.txt", "Myles Jack wasn't down\n", tmp_path)


@pytest.fixture
def project_shared_file(tmp_path: Path) -> ProjectFiles:
    """
    Creates a project called "SharedFile" that has one file
    "shared.py" that was modified by three authors.

    Returns:
        ProjectFiles: The project file describing this project
    """

    project_dir = tmp_path / "SharedFile"
    project_dir.mkdir()
    repo = Repo.init(project_dir)
    filename = "shared.py"

    # Alice creates file
    with repo.config_writer() as config:
        config.set_value("user", "name", "Alice")
        config.set_value("user", "email", "alice@example.com")
    (project_dir / filename).write_text("# Initial version")
    repo.index.add([filename])
    repo.index.commit("Alice's initial commit")

    # Bob modifies same file
    with repo.config_writer() as config:
        config.set_value("user", "name", "Bob")
        config.set_value("user", "email", "bob@example.com")
    (project_dir / filename).write_text("# Modified by Bob")
    repo.index.add([filename])
    repo.index.commit("Bob's modification")

    # Charlie also modifies it
    with repo.config_writer() as config:
        config.set_value("user", "name", "Charlie")
        config.set_value("user", "email", "charlie@example.com")
    (project_dir / filename).write_text("# Modified by Charlie")
    repo.index.add([filename])
    repo.index.commit("Charlie's modification")

    return ProjectFiles(
        name="SharedFile",
        root_path=str(project_dir),
        file_paths=["shared.py"],
        repo=repo
    )


@pytest.fixture
def project_no_git_dir(tmp_path: Path) -> ProjectFiles:
    """
    Creates a not git project with two python files.

    Returns:
        tuple(str, list[str]) : Path to project folder, realtive
            path to files in project.
    """
    project_dir = tmp_path / "NoGitProject"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('No git')")
    (project_dir / "utils.py").write_text("# Utils")

    return ProjectFiles(
        name="NoGitProject",
        root_path=str(project_dir),
        file_paths=["main.py", "utils.py"],
        repo=None
    )
