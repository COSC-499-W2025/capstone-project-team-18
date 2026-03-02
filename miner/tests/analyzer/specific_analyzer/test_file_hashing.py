

import pytest
from src.core.analyzer import analyzer_util
from src.core.analyzer.analyzer_util import single_file_analysis
from src.core.analyzer.base_file_analyzer import BaseFileAnalyzer
from src.database.api.models import UserConfigModel
from src.core.project_discovery import project_discovery as pd


@pytest.fixture(autouse=True)
def mock_db_engines(monkeypatch, blank_db):
    """Ensure both analyzer + project discovery use test DB engine."""
    monkeypatch.setattr(analyzer_util, "get_engine", lambda: blank_db)
    monkeypatch.setattr(pd, "get_engine", lambda: blank_db)
    monkeypatch.setattr(
        pd, "get_project_report_model_by_name", lambda session, _: None)


def test_matching_hash_between_file_reports(
    tmp_path, create_temp_file, project_context_from_root
):
    # Arrange: two different files with identical content
    file_one = create_temp_file("one.txt", "Identical content", tmp_path)[1]
    file_two = create_temp_file("one.txt", "Identical content", tmp_path)[1]
    project_context = project_context_from_root(str(tmp_path))

    user = UserConfigModel()
    user.user_email = "same-user@example.com"

    report_one, _ = single_file_analysis(
        file_one, project_context.name, user, project_context, str(file_one))
    report_two, _ = single_file_analysis(
        file_two, project_context.name, user, project_context, str(file_two))

    analyzer_one = BaseFileAnalyzer(
        user, project_context, str(file_one)
    )
    analyzer_two = BaseFileAnalyzer(
        user, project_context, str(file_two)
    )

    print(analyzer_one.hashed_content)

    # Assert: hashes must match for identical content + same user salt
    assert analyzer_one.hashed_content == analyzer_two.hashed_content


def test_hash_salt_by_email(
    tmp_path, create_temp_file, project_context_from_root
):
    file_info = create_temp_file("same.txt", "Same content", tmp_path)
    project_context = project_context_from_root(str(tmp_path))

    user_one = UserConfigModel()
    user_one.user_email = "first@example.com"
    analyzer_one = BaseFileAnalyzer(
        user_one, project_context, file_info[1]
    )

    user_two = UserConfigModel()
    user_two.user_email = "second@example.com"
    analyzer_two = BaseFileAnalyzer(
        user_two, project_context, file_info[1]
    )

    assert analyzer_one.hashed_content != analyzer_two.hashed_content
