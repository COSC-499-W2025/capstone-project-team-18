from pathlib import Path

import pytest
from pytest import approx

from src.core.analyzer import extract_file_reports, analyzer_util
from src.core.project_discovery.project_discovery import ProjectLayout
from src.core.report import ProjectReport
from src.core.report.project.project_statistics import \
    ProjectActivityTypeContributions
from src.core.statistic import (FileDomain, ProjectStatCollection)
from src.database.api.models import UserConfigModel


@pytest.fixture(autouse=True)
def mock_analyzer_db_engine(monkeypatch, blank_db):
    monkeypatch.setattr(analyzer_util, "get_engine", lambda: blank_db)


def test_activity_contribution_from_non_tracked_project(tmp_path, make_project_layout, mock_readme_analysis):
    """
    Tests that in a normal project,
    we see normal activity contributions.
    """

    pf = ProjectLayout(
        name="act_contrb",
        root_path=Path(f"{tmp_path}/act_contrb"),
        file_paths=[
            Path("tests/my_1test.py"),
            Path("test/my_2test.py"),
            Path("README.md"),
            Path("code1.py"),
            Path("code2.py"),
            Path("code3.py")
        ],
        repo=None,
        pre_analyzed=False,
    )

    make_project_layout(pf)

    frs, _ = extract_file_reports(pf, UserConfigModel())

    pr_email = ProjectReport(
        file_reports=frs,
        project_path=str(pf.root_path),
        project_name=pf.name,
        user_email="bob@example.com",
        calculator_classes=[
            ProjectActivityTypeContributions
        ]
    )

    pr_no_email = ProjectReport(
        file_reports=frs,
        project_path=str(pf.root_path),
        project_name=pf.name,
        user_email=None,
        calculator_classes=[
            ProjectActivityTypeContributions
        ]
    )

    for pr in [pr_email, pr_no_email]:
        contr = pr.get_value(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value)

        assert contr[FileDomain.TEST] == approx(2/6)
        assert contr[FileDomain.DOCUMENTATION] == approx(1/6)
        assert contr[FileDomain.CODE] == approx(3/6)


def test_activity_contribution_from_git_project(project_realistic, mock_readme_analysis):
    """
    Test that for a Gitproject, we accuractly
    count the contribution percentage
    """

    uc = UserConfigModel()
    uc.user_email = "bob@example.com"

    frs, _ = extract_file_reports(project_realistic, uc)

    pr = ProjectReport(
        file_reports=frs,
        project_path=str(project_realistic.root_path),
        project_name=project_realistic.name,
        project_repo=project_realistic.repo,
        user_email=uc.user_email,
        calculator_classes=[
            ProjectActivityTypeContributions
        ]
    )

    # Adjusted to include uncontributed files in case of use for semantic analysis
    # All activty type contributions should remain the same however
    assert frs is not None and len(frs) == 7
    contrib_flags = [f.is_info_file is False for f in frs]
    assert contrib_flags.count(True) == 5
    assert contrib_flags.count(False) == 2

    contr = pr.get_value(
        ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value)

    # Bob added...
    # data.db local file that should be ignored as it has no file domain
    # helpers.py 3 / 3 lines CODE
    # test_main 2 / 2 lines TEST
    # schema.sql 1 / 3 lines CODE
    # README.md  2 / 5 line DOC

    # Which means in all,
    # 4 / 8 CODE
    # 2 / 8 TEST
    # 2 / 8 DOC

    assert contr[FileDomain.CODE] == approx(4/8)
    assert contr[FileDomain.TEST] == approx(2/8)
    assert contr[FileDomain.DOCUMENTATION] == approx(2/8)

    assert contr[FileDomain.CODE] == approx(4/8)
    assert contr[FileDomain.TEST] == approx(2/8)
    assert contr[FileDomain.DOCUMENTATION] == approx(2/8)
