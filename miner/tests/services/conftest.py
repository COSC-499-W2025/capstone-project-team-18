import pytest
from sqlmodel import Session
from datetime import datetime

from src.core.report import ProjectReport
from src.database.api.CRUD.projects import save_project_report
from src.core.statistic import Statistic, ProjectStatCollection
from src.core.statistic.statistic_models import WeightedSkills, CodingLanguage, FileDomain


@pytest.fixture
def pr1(project_report_from_stats) -> ProjectReport:
    # 1. Define specific statistics
    stats = [
        Statistic(
            ProjectStatCollection.PROJECT_START_DATE.value,
            datetime(2024, 1, 1)  # Changed to datetime
        ),
        Statistic(
            ProjectStatCollection.IS_GROUP_PROJECT.value,
            True
        ),
        Statistic(
            ProjectStatCollection.TOTAL_AUTHORS.value,
            4
        ),
        Statistic(
            ProjectStatCollection.USER_COMMIT_PERCENTAGE.value,
            28.5
        ),
        Statistic(
            ProjectStatCollection.PROJECT_TAGS.value,
            ["pytest", "python-backend", "data-modeling"]
        ),
        Statistic(
            ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
            {CodingLanguage.PYTHON: 0.8, CodingLanguage.SQL: 0.2}
        ),
        Statistic(
            ProjectStatCollection.ACTIVITY_METRICS.value,
            {"avg_commits_per_week": 5.5, "consistency_score": 0.92}
        ),
        Statistic(
            ProjectStatCollection.ROLE_DESCRIPTION.value,
            "Lead Backend Developer responsible for data persistence layer."
        )
    ]

    # 2. Use the factory fixture to build the ProjectReport
    return project_report_from_stats(
        statistics=stats,
        project_name="pr1"
    )


@pytest.fixture
def pr2(project_report_from_stats) -> ProjectReport:
    # 1. Define stats for a UI-focused project
    stats = [
        Statistic(
            ProjectStatCollection.PROJECT_START_DATE.value,
            datetime(2025, 5, 10)  # Changed to datetime
        ),
        Statistic(
            ProjectStatCollection.IS_GROUP_PROJECT.value,
            False  # Solo project
        ),
        Statistic(
            ProjectStatCollection.TOTAL_PROJECT_LINES.value,
            4200
        ),
        Statistic(
            ProjectStatCollection.PROJECT_FRAMEWORKS.value,
            [
                WeightedSkills("React", 1.0),
                WeightedSkills("TailwindCSS", 0.8),
                WeightedSkills("Zustand", 0.4)
            ]
        ),
        Statistic(
            ProjectStatCollection.ACTIVITY_TYPE_CONTRIBUTIONS.value,
            {
                FileDomain.DOCUMENTATION: 0.10
            }
        ),
        Statistic(
            ProjectStatCollection.PROJECT_TONE.value,
            "Creative and accessible"
        ),
        Statistic(
            ProjectStatCollection.WORK_PATTERN.value,
            "burst"  # Focused work over a short period
        ),
        Statistic(
            ProjectStatCollection.COMMIT_TYPE_DISTRIBUTION.value,
            {
                "feat": 60.0,
                "fix": 15.0,
                "style": 25.0
            }
        )
    ]

    return project_report_from_stats(
        statistics=stats,
        project_name="pr2"
    )


@pytest.fixture
def pr2_updated(project_report_from_stats) -> ProjectReport:
    # 1. Stats reflecting growth after a later analysis
    stats = [
        Statistic(
            ProjectStatCollection.PROJECT_START_DATE.value,
            datetime(2025, 5, 10)  # Changed to datetime
        ),
        # Total lines jumped from 4,200 to 12,500
        Statistic(
            ProjectStatCollection.TOTAL_PROJECT_LINES.value,
            12500
        ),
        # Now reflects more authors as the project grew
        Statistic(
            ProjectStatCollection.TOTAL_AUTHORS.value,
            3
        ),
        # Frameworks now include backend/data tools
        Statistic(
            ProjectStatCollection.PROJECT_FRAMEWORKS.value,
            [
                WeightedSkills("React", 0.9),
                WeightedSkills("TailwindCSS", 0.7),
                WeightedSkills("FastAPI", 0.6),
                WeightedSkills("Pandas", 0.5)
            ]
        ),
        # Language ratio shifted from pure TS/JS to include Python
        Statistic(
            ProjectStatCollection.CODING_LANGUAGE_RATIO.value,
            {
                CodingLanguage.TYPESCRIPT: 0.55,
                CodingLanguage.PYTHON: 0.40,
                CodingLanguage.CSS: 0.05
            }
        ),
        # Updated role to reflect the expanded scope
        Statistic(
            ProjectStatCollection.ROLE_DESCRIPTION.value,
            "Full-stack developer; transitioned project from a static UI to a data-driven application."
        ),
        # Work pattern changed from 'burst' to 'consistent' over the longer timeline
        Statistic(
            ProjectStatCollection.WORK_PATTERN.value,
            "consistent"
        )
    ]

    return project_report_from_stats(
        statistics=stats,
        project_name="pr2"
    )


@pytest.fixture
def prs_db(blank_db, pr1, pr2):
    with Session(blank_db) as session:
        save_project_report(session, pr1, None, False)
        save_project_report(session, pr2, None, False)
        session.commit()

    yield blank_db
