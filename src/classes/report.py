"""
Reports hold statistics.
"""
from typing import Any, Optional
from pathlib import Path
import tempfile
import shutil
import zipfile
from git import Repo, InvalidGitRepositoryError
from .statistic import Statistic, StatisticTemplate, StatisticIndex, ProjectStatCollection, FileStatCollection, UserStatCollection, WeightedSkills
from typing import Any
from datetime import datetime, date


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
        """
        Initialize ProjectReport with file reports and optional Git analysis from zip file.
        
        Args:
            file_reports: List of FileReport objects to aggregate statistics from
            zip_path: Optional path to zip file for Git analysis
            project_name: Optional project name for Git analysis
        """
        project_stats = []
        
        # Process file reports if provided
        if file_reports:
            # Extract all creation dates from file reports, filtering out None values
            date_created_list = [
                report.get_value(FileStatCollection.DATE_CREATED.value) 
                for report in file_reports 
                if report.get_value(FileStatCollection.DATE_CREATED.value) is not None
            ]

            # Extract all modification dates from file reports, filtering out None values  
            date_modified_list = [
                report.get_value(FileStatCollection.DATE_MODIFIED.value) 
                for report in file_reports 
                if report.get_value(FileStatCollection.DATE_MODIFIED.value) is not None
            ]

            # Calculate and add project start date (earliest file creation)
            if date_created_list:
                start_date = min(date_created_list)
                project_start_stat = Statistic(ProjectStatCollection.PROJECT_START_DATE.value, start_date)
                project_stats.append(project_start_stat)

            # Calculate and add project end date (latest file modification)
            if date_modified_list:
                end_date = max(date_modified_list)
                project_end_stat = Statistic(ProjectStatCollection.PROJECT_END_DATE.value, end_date)
                project_stats.append(project_end_stat)

        # Create StatisticIndex with project-level statistics
        project_statistics = StatisticIndex(project_stats)
        
        # Add Git analysis statistics if zip file is provided
        if zip_path and project_name:
            git_stats = self._analyze_git_authorship(zip_path, project_name)
            if git_stats:
                for stat in git_stats:
                    project_statistics.add(stat)
        
        # Initialize the base class with the project statistics
        super().__init__(project_statistics)
        
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
    This UserReport class hold Statistics about the user. It is made
    from many different ReportReports
    """

    def __init__(self, file_reports: list[ProjectReport]):

        # Here we would take all the file stats and turn them into user stats

        raise ValueError("Unimplemented")
        return super().__init__(None)

    @classmethod
    def from_statistics(cls, statistics: StatisticIndex) -> "UserReport":
        inst = cls.__new__(cls)
        BaseReport.__init__(inst, statistics)
        return inst

    @staticmethod
    def _fmt_mdy(d: datetime | date | None) -> str:
        if d is None:
            return "an unknown date"
        if isinstance(d, date) and not isinstance(d, datetime):
            d = datetime(d.year, d.month, d.day)
        return f"{d.month}/{d.day}/{d.year}"

    @staticmethod
    def _coerce_datetime(val: Any) -> datetime | None:
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime(val.year, val.month, val.day)
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val)
            except Exception:
                return None
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%fZ"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    pass
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                return None
        return None

    @staticmethod
    def _title_from_name(raw: str) -> str:
        s = raw.replace("_", " ").replace("-", " ").strip().lower().title()
        return s

    def to_user_readable_string(self) -> str:
        """
        For every statistic in self.statistics, return a human-readable line.
        Known user stats get custom phrasing; others fall back to 'Title: value'.
        """
        if self.statistics is None or len(self.statistics) == 0:
            return "No user statistics are available yet."

        lines: list[str] = []

        for stat in self.statistics:
            template = stat.get_template()
            name = template.name 
            value = stat.value

            if name == UserStatCollection.USER_START_DATE.value.name:
                dt = self._coerce_datetime(value)
                lines.append(
                    f"You started your first project on {self._fmt_mdy(dt)}!"
                )
                continue

            if name == UserStatCollection.USER_END_DATE.value.name:
                dt = self._coerce_datetime(value)
                lines.append(
                    f"Your latest contribution was on {self._fmt_mdy(dt)}."
                )
                continue

            if name == UserStatCollection.USER_SKILLS.value.name:
                skills_line = "an unknown set of skills"
                try:
                    if isinstance(value, list) and value:
                        def _skill_str(ws: WeightedSkills) -> str:
                            n = getattr(ws, "skill_name", None) or str(ws)
                            w = getattr(ws, "weight", None)
                            return f"{n} ({w})" if w is not None else f"{n}"
                        skills_line = ", ".join(_skill_str(ws) for ws in value)
                except Exception:
                    pass
                lines.append(f"Your skills include: {skills_line}.")
                continue
            
            title = self._title_from_name(name)
            
            should_try_date = (
                template.expected_type in (date, datetime)
                or isinstance(value, (date, datetime))
                or isinstance(value, str) 
            )
            maybe_dt = self._coerce_datetime(value) if should_try_date else None
            
            if maybe_dt:
                lines.append(f"{title}: {self._fmt_mdy(maybe_dt)}")
            else:
                lines.append(f"{title}: {value!r}")
                
        return "\n".join(lines)
