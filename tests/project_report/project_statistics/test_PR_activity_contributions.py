from pathlib import Path
from pytest import approx
from src.core.report import ProjectReport
from src.core.project_discovery.project_discovery import ProjectLayout
from src.core.analyzer import extract_file_reports
from src.core.statistic import ProjectStatCollection, FileDomain


def test_activity_contribution_from_non_tracked_project(tmp_path, make_project_layout):
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
        repo=None
    )

    make_project_layout(pf)

    frs = extract_file_reports(pf)

    pr_email = ProjectReport(
        file_reports=frs,
        project_path=str(pf.root_path),
        project_name=pf.name,
        user_email="bob@example.com"
    )

    pr_no_email = ProjectReport(
        file_reports=frs,
        project_path=str(pf.root_path),
        project_name=pf.name,
        user_email=None
    )

    for pr in [pr_email, pr_no_email]:
        contr = pr.get_value(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value)

        assert contr[FileDomain.TEST] == approx(2/6)
        assert contr[FileDomain.DOCUMENTATION] == approx(1/6)
        assert contr[FileDomain.CODE] == approx(3/6)


def test_activity_contribution_from_git_project(project_realistic):
    """
    Test that for a Gitproject, we accuractly
    count the contribution percentage
    """

    my_email = "bob@example.com"

    frs = extract_file_reports(project_realistic, email=my_email)

    pr = ProjectReport(
        file_reports=frs,
        project_path=str(project_realistic.root_path),
        project_name=project_realistic.name,
        project_repo=project_realistic.repo,
        user_email=my_email
    )

    # Check to see that files are only included if the user themselves
    # contributed and local
    assert frs is not None and len(frs) == 5

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
