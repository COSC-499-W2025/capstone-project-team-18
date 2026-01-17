from pathlib import Path
from src.classes.analyzer import extract_file_reports
from src.utils.project_discovery.project_discovery import discover_projects
import tempfile
from pathlib import Path

from src.utils.zipped_utils import unzip_file
from src.utils.project_discovery.project_discovery import discover_projects
from src.classes.analyzer import extract_file_reports
from src.classes.statistic import ProjectStatCollection
from src.classes.report import ProjectReport


def test_verify_accurate_contribution_percentage(resource_dir):
    """
    Sam has a project in the resource directory that he solo
    made. This test will test to make sure that when we analyze
    this project, it says 100% contribution.
    """
    project_filename = "sample_git_project_one_author.zip"
    email = "sikora.samj@gmail.com"

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

    assert 100 == project_report.get_value(
        ProjectStatCollection.TOTAL_CONTRIBUTION_PERCENTAGE.value)
