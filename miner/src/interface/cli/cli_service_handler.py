"""
Functions that allow the CLI to interact with the services
"""

from typing import Optional, Callable
import os
import warnings
import logging
from datetime import datetime
from pathlib import Path

from sqlmodel import Session

from src.services.mining_service import start_miner_service, MinerResults
from src.services.preferences.preference_service import UserConfig
from src.interface.cli.user_preferences import UserPreferences
from src.core.report import UserReport
from src.interface.cli.print_resume_and_portfolio import resume_CLI_stringify, portfolio_CLI_stringify
from src.core.resume.render import ResumeLatexRenderer
from src.database.api.models import UserConfigModel as UserConfig


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

    # Keep ML enabled in CLI, but silence model loading noise/progress bars.
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    # Silence noisy warnings from ML stack (e.g., UMAP/BERTopic) in CLI output.
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    # Ensure root logger does not emit to console.
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
