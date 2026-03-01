
from pathlib import Path

from sqlmodel import Session
from src.core.analyzer.analyzer_util import single_file_analysis
from src.core.analyzer.base_file_analyzer import BaseFileAnalyzer
from src.core.report.file_report import FileReport
from src.core.statistic.base_classes import Statistic, StatisticIndex
from src.core.statistic.file_stat_collection import FileStatCollection
from src.database.api.models import UserConfigModel
from src.database.core.model_serializer import serialize_file_report


def test_file_analysis_when_hash_matches(
    tmp_path, create_temp_file, project_context_from_root, blank_db, monkeypatch
):
    file_info = create_temp_file("dup.unknown", "duplicate content", tmp_path)
    project_context = project_context_from_root(str(tmp_path))

    analyzer = BaseFileAnalyzer(
        UserConfigModel(), project_context, file_info[1]
    )

    stats = StatisticIndex([
        Statistic(
            FileStatCollection.FILE_SIZE_BYTES.value,
            Path(analyzer.filepath).stat().st_size
        )
    ])

    file_report = FileReport(
        statistics=stats,
        filepath=analyzer.filepath,
        is_info_file=False,
        file_hash=analyzer.hashed_content,
        project_name=project_context.name,
    )

    model = serialize_file_report(file_report)

    with Session(blank_db) as session:
        session.add(model)
        session.commit()

    monkeypatch.setattr(
        "src.core.analyzer.analyzer_util.get_engine",
        lambda: blank_db
    )
    monkeypatch.setattr(
        "src.core.analyzer.base_file_analyzer.get_engine",
        lambda: blank_db
    )

    def fail_analyze(self):
        raise AssertionError("analyze should not run for duplicate hash")

    monkeypatch.setattr(BaseFileAnalyzer, "analyze", fail_analyze)

    result = single_file_analysis(
        Path(file_info[1]),
        project_context.name,
        UserConfigModel(),
        project_context,
        file_info[1],
    )

    assert result is not None
    assert result.file_hash == analyzer.hashed_content
    assert result.filepath == analyzer.filepath


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
