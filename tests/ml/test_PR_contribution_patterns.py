from datetime import datetime, timedelta
from src.core.report.project.project_statistics import ProjectContributionPatterns
from src.core.statistic import ProjectStatCollection

class _Author:
    def __init__(self, email):
        self.email = email

class _Commit:
    def __init__(self, email, message, ts):
        self.author = _Author(email)
        self.message = message
        self.authored_date = ts

class _Repo:
    def __init__(self, commits):
        self._commits = commits
    def iter_commits(self):
        return self._commits

class _Report:
    def __init__(self, repo, email):
        self.project_repo = repo
        self.email = email
        self.project_name = "TestProj"
        self._values = {
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value: 50.0,
            ProjectStatCollection.TOTAL_AUTHORS.value: 3,
            ProjectStatCollection.IS_GROUP_PROJECT.value: True,
        }
    def get_value(self, key):
        return self._values.get(key)

def test_contribution_patterns_calculate():
    base = datetime.now()
    commits = [
        _Commit("me@example.com", "feat: add feature", base.timestamp()),
        _Commit("me@example.com", "fix: bug", (base + timedelta(days=1)).timestamp()),
        _Commit("me@example.com", "docs: update docs", (base + timedelta(days=2)).timestamp()),
    ]
    report = _Report(_Repo(commits), "me@example.com")
    calc = ProjectContributionPatterns()
    stats = calc.calculate(report)

    # Check that we got the expected statistics back
    assert len(stats) == 5, f"Expected 5 stats, got {len(stats)}"

    # Use get_template() method to access the template
    keys = {s.get_template().name for s in stats}
    assert "COMMIT_TYPE_DISTRIBUTION" in keys
    assert "WORK_PATTERN" in keys
    assert "COLLABORATION_ROLE" in keys
    assert "ROLE_DESCRIPTION" in keys
    assert "ACTIVITY_METRICS" in keys