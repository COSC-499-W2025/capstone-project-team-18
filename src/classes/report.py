"""
Reports hold statistics.
"""
from typing import Any, Optional
from pathlib import Path
import tempfile
import shutil
import zipfile
from git import Repo, InvalidGitRepositoryError
from .statistic import Statistic, StatisticTemplate, StatisticIndex, ProjectStatCollection


class BaseReport:
    """
    This is the BaseReport class. A report is a class that holds
    statistics.
    """

    def __init__(self, statistics: StatisticIndex):
        self.statistics = statistics

    def add_statistic(self, stat: Statistic):
        self.statistics.add(stat)

    def get(self, template: StatisticTemplate):
        return self.statistics.get(template)

    def get_value(self, template: StatisticTemplate) -> Any:
        return self.statistics.get_value(template)

    def to_dict(self) -> dict[str, Any]:
        return self.statistics.to_dict()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.to_dict()}>"


class FileReport(BaseReport):
    """
    The FileReport class is the lowest level report. It is made
    by file-type specific, analyzers.
    """

    filepath: str

    def __init__(self, statistics: StatisticIndex, filepath: str):
        super().__init__(statistics)
        self.filepath = filepath

    def get_filename(self):
        raise ValueError("Unimplemented")


class ProjectReport(BaseReport):
    """
    The ProjectReport class utilizes many FileReports to
    create many Project Statistics about a single project.

    For example, maybe we sum up all the lines of written
    in a FileReport to create a project level statistics
    of "total lines written."
    """

    def __init__(self, file_reports: list[FileReport] = None, zip_path: str = None, project_name: str = None):
        """Initialize ProjectReport with optional Git analysis from zip file."""
        statistics = StatisticIndex()
        if zip_path and project_name:
            git_stats = self._analyze_git_authorship(zip_path, project_name)
            if git_stats:
                for stat in git_stats:
                    statistics.add(stat)
        super().__init__(statistics)

    def _analyze_git_authorship(self, zip_path: str, project_name: str) -> Optional[list[Statistic]]:
        """Analyzes Git commit history to determine authorship statistics."""
        if not Path(zip_path).exists():
            return None

        temp = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                files = [f for f in zf.namelist(
                ) if f.startswith(f"{project_name}/")]
                if not files:
                    return None
                for path in files:
                    zf.extract(path, temp)

            try:
                repo = Repo(Path(temp) / project_name)
                all_authors = {c.author.email for c in repo.iter_commits()}
                total_authors = len(all_authors)

                authors_per_file = {}
                for item in repo.tree().traverse():
                    if item.type == 'blob':
                        try:
                            file_authors = {
                                c.author.email for c in repo.iter_commits(paths=item.path)}
                            authors_per_file[item.path] = len(file_authors)
                        except Exception:
                            continue

                return [
                    Statistic(
                        ProjectStatCollection.IS_GROUP_PROJECT.value, total_authors > 1),
                    Statistic(
                        ProjectStatCollection.TOTAL_AUTHORS.value, total_authors),
                    Statistic(
                        ProjectStatCollection.AUTHORS_PER_FILE.value, authors_per_file)
                ]
            except InvalidGitRepositoryError:
                return None
        except (zipfile.BadZipFile, FileNotFoundError):
            return None
        finally:
            shutil.rmtree(temp, ignore_errors=True)


class UserReport(BaseReport):
    """
    This UserReport class hold Statstics about the user. It is made
    from many different ProjectReports
    """

    def __init__(self, file_reports: list[ProjectReport]):

        # Here we would take all the file stats and turn them into user stats

        raise ValueError("Unimplemented")
        return super().__init__(None)
