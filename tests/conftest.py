"""
This file will run everytime pytest
starts running tests. It is used to
make global changes to the testing environment.

Fixtures that we want/need to access for (nearly) every
test will live in here. Then, we can import the fixture into
the test file when we need them.
"""
import pytest
import sys
import random
import datetime
from pathlib import Path
from datetime import timedelta
from typing import Optional

from git import Repo

from src.classes.statistic import StatisticIndex, Statistic, FileStatCollection, ProjectStatCollection, UserStatCollection
from src.classes.report import FileReport, ProjectReport, UserReport
from src.utils.project_discovery import ProjectFiles
from tests.utils.helper_functions import get_temp_file


# contributor (set[str]): Optional, if the file is in a directory with multiple contributors, include this file contributor's name & email.
# - Example: `contributor = ('Spencer', 'spencer@test.com')`


# --- Fixtures --

RESOURCE_DIR = Path(__file__).parent / "tests/resources"

# Logicially the same as `get_temp_file`, w/out manual setup overhead


@pytest.fixture
def temp_txt_file(tmp_path: Path) -> Path:
    """
    Creates a temporary text file. Use this fixture when testing
    a feature that is dependent on metadata that makes up the file

    Returns:
        Path: A `Path` object for the fixture text file
    """
    text = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas nec
                velit a ante pulvinar euismod in blandit enim. Phasellus vel nibh a elit
                consequat pretium. Nullam eleifend sapien ut rhoncus porta. Nam tincidunt
                nisl nunc, sit amet vulputate felis finibus in. Morbi vitae velit purus.
                Nulla varius tellus purus, convallis tristique erat molestie vitae.
                Pellentesque dictum purus sit amet sollicitudin luctus. Proin placerat urna
                id dignissim bibendum. Donec vestibulum massa vitae urna scelerisque, in
                pretium erat convallis. Sed lobortis orci id nibh malesuada, nec molestie
                ipsum euismod. Nam interdum egestas nisi vel luctus. Donec eget elit
                venenatis, gravida orci varius, ultrices quam. Praesent vel felis erat.'''

    return get_temp_file(filename="text.txt", content=text, path=tmp_path)


'''
@pytest.fixture
def temp_py_file(tmp_path: Path) -> Path:
    # TODO


def temp__file(tmp_path: Path) -> Path:
'''


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
