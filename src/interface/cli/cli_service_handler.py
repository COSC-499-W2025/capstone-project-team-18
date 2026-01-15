"""
Functions that allow the CLI to interact with the services
"""

from typing import Optional, Callable
from pathlib import Path

from src.utils.print_resume_and_portfolio import resume_CLI_stringify, portfolio_CLI_stringify
from src.core.resume.render import ResumeLatexRenderer
from src.infrastructure.log.logging import get_logger
from src.services.mining_service import start_miner_service, MinerResults
from src.interface.cli.user_preferences import UserPreferences

logger = get_logger(__name__)


def start_miner_cli(
    zipped_file_path: str,
    email: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None
) -> None:
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

    prefs = UserPreferences()
    zipped_file = Path(zipped_file_path)

    language_filter = prefs.get("languages_to_include", [])
    user_report_title = zipped_file.stem
    zipped_file_format = zipped_file.suffix

    file_bytes = None
    with open(zipped_file, 'rb') as f:
        file_bytes = f.read()

    # Run the main service
    miner_results: MinerResults = start_miner_service(
        zipped_bytes=file_bytes,
        zipped_format=zipped_file_format,
        user_report_title=user_report_title,
        email=email,
        language_filter=language_filter,
        progress_callback=progress_callback
    )

    user_report = miner_results.user_report

    print("-------- Analysis Reports --------\n")
    resume = user_report.generate_resume(email)

    # Download latex resume to file system
    latex_str = resume.export(ResumeLatexRenderer())

    with open("resume.tex", "w", encoding="utf-8") as f:
        f.write(latex_str)

    # Print the resume items
    resume_CLI_stringify(resume)

    # Print the portfolio item
    portfolio_CLI_stringify(user_report)
