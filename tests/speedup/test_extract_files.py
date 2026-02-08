import time
import multiprocessing.dummy as mp_dummy

from src.core.analyzer import analyzer_util
from src.core.project_discovery.project_discovery import ProjectLayout
from src.core.report.file_report import FileReport
from src.core.statistic import StatisticIndex


class DummyAnalyzer:
    def __init__(self, relative_path: str):
        self.relative_path = relative_path

    def should_analyze_file(self) -> bool:
        return True

    def is_info_file(self) -> bool:
        return False

    def create_info_file(self) -> FileReport:
        return FileReport(StatisticIndex(), self.relative_path)

    def analyze(self) -> FileReport:
        time.sleep(0.01)
        return FileReport(StatisticIndex(), self.relative_path)


def sequential_extract_file_reports(project_file: ProjectLayout) -> list[FileReport]:
    reports = []

    for file in project_file.file_paths:
        result = analyzer_util.single_file_analysis(
            (
                str(project_file.root_path),
                file,
                project_file.repo.working_tree_dir if project_file.repo else None,
                None,
                None,
                None,
                project_file.name,
            )
        )
        if result is not None:
            reports.append(result)

    return reports


def test_extract_file_reports_parallel_speedup(project_realistic, monkeypatch):
    file_paths = project_realistic.file_paths * 30
    project = ProjectLayout(
        name=project_realistic.name,
        root_path=project_realistic.root_path,
        file_paths=file_paths,
        repo=project_realistic.repo,
    )

    def fake_get_appropriate_analyzer(
            _root_path,
            relative_path,
            _repo,
            _email,
            _github,
            _language_filter,
    ):
        return DummyAnalyzer(relative_path)

    monkeypatch.setattr(
        analyzer_util,
        "get_appropriate_analyzer",
        fake_get_appropriate_analyzer,
    )
    monkeypatch.setattr(analyzer_util, "Pool", mp_dummy.Pool)
    monkeypatch.setattr(analyzer_util, "cpu_count", lambda: 4)

    start = time.perf_counter()
    sequential_reports = sequential_extract_file_reports(project)
    sequential_time = time.perf_counter() - start

    start = time.perf_counter()
    parallel_reports = analyzer_util.extract_file_reports(project)
    parallel_time = time.perf_counter() - start

    # Speed up in testing showed as 2.77
    assert len(parallel_reports) == len(sequential_reports)
    assert parallel_time < sequential_time * 0.9
