"""
Functions that allow the CLI to interact with the services
"""

from typing import Optional, Callable, Any
import os
import warnings
import logging
from datetime import datetime
from pathlib import Path

from sqlmodel import Session

from src.services.mining_service import start_miner_service, MinerResults
from src.services.interview_service import (
    build_interview_context,
    evaluate_answer,
    generate_question,
    InterviewAnswerResult,
    InterviewStartResult,
)
from src.services.preferences.preference_service import UserConfig
from src.interface.cli.user_preferences import UserPreferences
from src.core.report import UserReport
from src.interface.cli.print_resume_and_portfolio import resume_CLI_stringify, portfolio_CLI_stringify
from src.core.resume.render import ResumeLatexRenderer
from src.database.api.models import UserConfigModel as UserConfig
from src.database.core.base import get_engine
from src.database.api.CRUD.projects import get_all_project_ids


def _configure_cli_ml_runtime() -> None:
    """Keep CLI ML output quiet and deterministic enough for terminal usage."""
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    root_logger.addHandler(logging.NullHandler())
    root_logger.setLevel(logging.CRITICAL)
    try:
        from transformers.utils import logging as hf_logging
        hf_logging.set_verbosity_error()
    except Exception:
        pass


def start_miner_cli(
    zipped_file_path: str,
    email: Optional[str] = None,
    github: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None
) -> MinerResults:
    """
    This is the CLI facing start miner application. It calls the
    start_miner_service. It is different because: this function assumes that the
    zipped file is a actual file on the computer, UserPreferences
    has relevant data, and that the results should be printed to the terminal.

    :param zipped_file_path: Path to the zipped file
    :type zipped_file_path: str
    :param email: Description
    :type email: Optional[str]
    :param progress_callback: Description
    :type progress_callback: Optional[Callable[[str, int, int, str], None]]
    """

    _configure_cli_ml_runtime()

    prefs = UserPreferences()
    zipped_file = Path(zipped_file_path)

    language_filter = prefs.get("languages_to_include", [])
    zipped_file_format = zipped_file.suffix

    file_bytes = None
    with open(zipped_file, 'rb') as f:
        file_bytes = f.read()

    # Run the main service
    miner_results: MinerResults = start_miner_service(
        zipped_bytes=file_bytes,
        zipped_format=zipped_file_format,
        user_config=UserConfig(
            consent=True,
            github=github,
            user_email=email,
        )
    )

    if miner_results.success is False:
        print("Error analyzing projects! Check logs for more info")
        return miner_results

    # make a UserReport with the ProjectReports
    user_report = UserReport(
        miner_results.project_reports, report_name=datetime.now().strftime("%d/%m:%S")
    )

    print("-------- Analysis Reports --------\n")
    resume = user_report.generate_resume(email, github)

    # Download latex resume to file system
    latex_str = resume.export(ResumeLatexRenderer())

    # Print the resume items
    resume_CLI_stringify(resume)

    # Print the portfolio item
    portfolio_CLI_stringify(user_report)

    return miner_results


def start_mock_interview_cli(
    *,
    job_description: str,
    difficulty: str = "intermediate",
    resume_id: int | None = None,
    project_names: list[str] | None = None,
) -> tuple[InterviewStartResult | None, dict[str, Any] | None]:
    _configure_cli_ml_runtime()

    engine = get_engine()
    with Session(engine) as session:
        selected_project_names = list(project_names or [])
        if resume_id is None and not selected_project_names:
            selected_project_names = get_all_project_ids(session)

        interview_context = build_interview_context(
            session=session,
            job_description=job_description,
            resume_id=resume_id,
            project_names=selected_project_names,
        )

    first_question = generate_question(
        job_description=job_description,
        interview_context=interview_context,
        difficulty=difficulty,
    )
    return first_question, interview_context


def answer_mock_interview_cli(
    *,
    job_description: str,
    interview_context: dict[str, Any],
    current_question: str,
    user_answer: str,
    difficulty: str = "intermediate",
) -> InterviewAnswerResult | None:
    _configure_cli_ml_runtime()
    return evaluate_answer(
        user_answer=user_answer,
        current_question=current_question,
        job_description=job_description,
        interview_context=interview_context,
        difficulty=difficulty,
    )
