"""
Tests for project-level aggregate statistics in ProjectReport.

This module tests the aggregate statistical methods that summarize
data across multiple file reports within a project.
"""
import pytest
from src.classes.report import ProjectReport, FileReport
from src.classes.statistic import StatisticIndex, FileStatCollection


class DummyFileReport(FileReport):
    """
    A dummy FileReport implementation for testing purposes.
    
    Simplifies testing by allowing direct creation of FileReports
    with specified statistics without needing actual file analysis.
    """
    
    def __init__(self, stats):
        """Initialize with a list of Statistic objects."""
        super().__init__(StatisticIndex(stats), filepath="dummy.txt")

    def get_value(self, template):
        """Retrieve statistic value by template."""
        return self.statistics.get_value(template)


@pytest.fixture
def sample_file_reports():
    """
    Fixture providing sample file reports for testing aggregate statistics.
    
    Creates a set of dummy file reports with varied types (code and documentation)
    and statistics to test ProjectReport aggregation methods.
    
    Returns:
        list[DummyFileReport]: List of 4 file reports with different characteristics
    """
    from src.classes.statistic import Statistic, FileDomain
    return [
        DummyFileReport([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 100),
            Statistic(FileStatCollection.TYPE_OF_FILE.value, FileDomain.CODE),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      ['numpy', 'pytest'])
        ]),
        DummyFileReport([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 50),
            Statistic(FileStatCollection.TYPE_OF_FILE.value, FileDomain.CODE),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      ['pytest', 'os'])
        ]),
        DummyFileReport([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 30),
            Statistic(FileStatCollection.TYPE_OF_FILE.value,
                      FileDomain.DOCUMENTATION),
            Statistic(FileStatCollection.ARI_WRITING_SCORE.value, 7.5)
        ]),
        DummyFileReport([
            Statistic(FileStatCollection.LINES_IN_FILE.value, 20),
            Statistic(FileStatCollection.TYPE_OF_FILE.value,
                      FileDomain.DOCUMENTATION),
            Statistic(FileStatCollection.ARI_WRITING_SCORE.value, 8.0)
        ])
    ]


def test_total_lines_of_code(sample_file_reports):
    """Test that total lines of code is correctly summed across all file reports."""
    pr = ProjectReport()
    pr.file_reports = sample_file_reports
    assert pr.get_total_lines_of_code() == 100 + 50 + 30 + 20


def test_language_distribution(sample_file_reports):
    """Test that file type distribution correctly counts code vs documentation files."""
    pr = ProjectReport()
    pr.file_reports = sample_file_reports
    dist = pr.get_language_distribution()
    assert dist['code'] == 2
    assert dist['documentation'] == 2


def test_code_to_doc_ratio(sample_file_reports):
    """Test that code-to-documentation ratio is correctly calculated."""
    pr = ProjectReport()
    pr.file_reports = sample_file_reports
    assert pr.get_code_to_doc_ratio() == 1.0  # 2 code / 2 doc


def test_average_ari_score(sample_file_reports):
    """Test that average ARI score is correctly calculated from documentation files."""
    pr = ProjectReport()
    pr.file_reports = sample_file_reports
    assert pr.get_average_ari_score() == pytest.approx((7.5 + 8.0) / 2)


def test_unique_imported_packages(sample_file_reports):
    """Test that unique imported packages are correctly aggregated across all files."""
    pr = ProjectReport()
    pr.file_reports = sample_file_reports
    pkgs = pr.get_unique_imported_packages()
    assert pkgs == {'numpy', 'pytest', 'os'}
