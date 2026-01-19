from pathlib import Path
import tempfile
import pytest

from src.utils.pathing_utils import unzip_file
from src.core.analyzer import extract_file_reports
from src.core.project_discovery.project_discovery import discover_projects
from src.core.statistic import ProjectStatCollection
from src.core.report import ProjectReport


@pytest.mark.parametrize(
    "email,percentage",
    [
        ("sikora.samj@gmail.com", 100),
        ("bob@gmail.com", 0),
        (None, None)
    ]
)
def test_verify_accurate_contribution_percentage(resource_dir, email, percentage):
    """
    Sam has a project in the resource directory that he solo
    made. This test will test to make sure that when we analyze
    this project, it says 100% contribution.
    """
    project_filename = "sample_git_project_one_author.zip"

    zipped_file = Path(resource_dir) / project_filename
    unzipped_dir = tempfile.mkdtemp(prefix="artifact_miner_")
    unzip_file(str(zipped_file), unzipped_dir)

    project = discover_projects(unzipped_dir)[0]

    file_reports = extract_file_reports(project, email, [])

    project_report = ProjectReport(
        project_name=project.name,
        project_path=project.root_path,
        project_repo=project.repo,
        file_reports=file_reports,
        user_email=email
    )

    assert percentage == project_report.get_value(
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)
