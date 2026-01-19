"""
This file handles all logic for logging
"""

import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = __file__


def get_logger(name: str, level=logging.INFO):
    """
    Function to return a configured logging object.

    :param name: The name of the logger. Should always be __name__ of the calling file
    :type name: str
    :param level: The level the logger should log at
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent logs from going to the terminal
    logger.propagate = False

    # Avoid adding multiple handlers if logger already has them
    if not logger.handlers:

        fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
        fh.setLevel(level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
2026-01-19 19:01:29 - src.classes.analyzer.analyzer_util - INFO - Skipping file test.js in project test_project
2026-01-19 19:01:29 - src.classes.analyzer.analyzer_util - INFO - Skipping file test.html in project test_project
2026-01-19 19:01:29 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:29 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.database.utils.database_access - INFO - Building ProjectReport obj for project with name Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:30 - src.database.utils.database_access - INFO - Building ProjectReport obj for project with name noFileReports
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.database.utils.database_access - INFO - Building ProjectReport obj for project with name Project1
2026-01-19 19:01:30 - src.database.utils.database_access - INFO - Building ProjectReport obj for project with name Project2
2026-01-19 19:01:30 - src.database.utils.database_access - INFO - Building ProjectReport obj for project with name proj
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.database.utils.database_access - INFO - Building ProjectReport obj for project with name Project2
2026-01-19 19:01:30 - src.database.utils.database_access - INFO - Building ProjectReport obj for project with name Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:30 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:31 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project1
2026-01-19 19:01:31 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Project2
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_discover_multiple_project0/extracted/Assignment2 is a project.
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_discover_multiple_project0/extracted/Assignment1 is a project.
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_discover_multiple_project0/extracted/FinalProject is a project.
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_discover_git_projects0/SoloProject is a project.
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_discover_git_projects0/TeamProject is a project.
2026-01-19 19:01:31 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SoloProject
2026-01-19 19:01:31 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project TeamProject
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_no_git_projects0/nogit_extracted/BasicProject is a project.
2026-01-19 19:01:31 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project BasicProject
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_mac_zip_structure0/mac_extracted/Projects is NOT a project. Iterating through it's subfolders...
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_mac_zip_structure0/mac_extracted/Projects/ProjectA is a project.
2026-01-19 19:01:31 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/pytest-of-vscode/pytest-25/test_mac_zip_structure0/mac_extracted/Projects/ProjectB is a project.
2026-01-19 19:01:31 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SoloProject
2026-01-19 19:01:31 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project TeamProject
2026-01-19 19:01:39 - src.ML.models.readme_analysis.readme_insights - INFO - Single README detected; using keyphrase fallback for themes
2026-01-19 19:01:39 - src.ML.models.readme_analysis.readme_insights - INFO - Single README detected; using keyphrase fallback for themes
2026-01-19 19:01:39 - src.classes.analyzer.analyzer_util - INFO - Skipping file app/main.py in project RealisticProject
2026-01-19 19:01:39 - src.classes.analyzer.analyzer_util - INFO - Skipping file scripts/bootstrap.sh in project RealisticProject
2026-01-19 19:01:45 - src.ML.models.readme_analysis.readme_insights - INFO - Single README detected; using keyphrase fallback for themes
2026-01-19 19:01:45 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project Unknown Project
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SoloProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project TeamProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project UnequalProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project UnequalProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project TeamProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SoloProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project TeamProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project NonexistentProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project AnyProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project NoGitProject
2026-01-19 19:01:46 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SoloProject
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SharedFile
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project EmptyRepo
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project RoundingProject
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project TeamProject
2026-01-19 19:01:47 - src.classes.analyzer.analyzer_util - INFO - Skipping file fileA.py in project SelectiveProject
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SelectiveProject
2026-01-19 19:01:47 - src.classes.analyzer.analyzer_util - INFO - Skipping file fileA.py in project NoContributionProject
2026-01-19 19:01:47 - src.classes.analyzer.analyzer_util - INFO - Skipping file fileB.py in project NoContributionProject
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project NoContributionProject
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project SingleAuthorProject
2026-01-19 19:01:47 - src.classes.analyzer.analyzer_util - INFO - Skipping file fileB.py in project ThreeWayProject
2026-01-19 19:01:47 - src.classes.analyzer.analyzer_util - INFO - Skipping file fileC.py in project ThreeWayProject
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project ThreeWayProject
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - README path not found for themes: Unknown Path/README.md
2026-01-19 19:01:47 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project ProjectTagsTest
2026-01-19 19:01:49 - src.classes.report.project.project_statistics - INFO - README path not found for themes: Unknown Path/README.md
2026-01-19 19:01:49 - src.classes.report.project.project_statistics - INFO - No README files found for theme extraction in project ProjectTagsTest
2026-01-19 19:01:49 - src.ML.models.readme_analysis.readme_insights - INFO - Single README detected; using keyphrase fallback for themes
2026-01-19 19:01:49 - src.utils.project_discovery.project_discovery - INFO - Directory /tmp/artifact_miner_f8ln9q3l/bayesian-scRNAseq-label-transfer is a project.
