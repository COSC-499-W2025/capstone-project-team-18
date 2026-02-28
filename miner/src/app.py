"""
The entry point for the ArtifactMiner program.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running `python miner/src/app.py` without manually setting PYTHONPATH.
_PKG_ROOT = Path(__file__).resolve().parents[1]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from src.infrastructure.log.logging import get_logger
from src.core.ML.models.azure_openai_runtime import azure_openai_enabled

logger = get_logger(__name__)

# Load local developer environment overrides (e.g., Azure keys in .env).
load_dotenv()


def _init_db() -> None:
    """
    Initialize database schema at startup.
    """
    from sqlmodel import SQLModel
    from src.database.core.base import get_engine
    SQLModel.metadata.create_all(get_engine())


def init_system() -> tuple[bool, str]:
    """
    This function does any setup and warmup tasks that are needed for a cold
    session start for the system. This includes both database configuration
    and ML warm-up.
    """
    if os.environ.get("ARTIFACT_MINER_WARMUP_MODELS", "1") == "0":
        message = "ML warmup disabled via env variable."
        logger.info(message)
        return False, message

    try:
        from src.core.ML.models.contribution_analysis.summary_generator import _load_model as load_signature_model
        from src.core.ML.models.contribution_analysis.project_summary_generator import _load_model as load_project_model
        from src.core.ML.models.contribution_analysis.commit_classifier import _get_commit_classifier
        from src.core.ML.models.contribution_analysis.role_analyzer import _get_role_classifier
        from src.core.ML.models.readme_analysis.readme_insights import _get_classifier as get_readme_tone_classifier
        from src.core.ML.models.readme_analysis.permissions import ml_extraction_allowed

        loaded_components: list[str] = []

        if azure_openai_enabled():
            loaded_components.append("azure openai provider")
            if _get_commit_classifier() is not None:
                loaded_components.append("commit classifier")
            if _get_role_classifier() is not None:
                loaded_components.append("role classifier")
            if get_readme_tone_classifier() is not None:
                loaded_components.append("README tone classifier")
            message = f"ML warmup complete: {', '.join(loaded_components)} ready."
            logger.info(message)
            return True, message

        if ml_extraction_allowed():
            signature_model, signature_tokenizer = load_signature_model()
            if signature_model is not None and signature_tokenizer is not None:
                loaded_components.append("signature summary")

            project_model, project_tokenizer = load_project_model()
            if project_model is not None and project_tokenizer is not None:
                loaded_components.append("project summary")

        if _get_commit_classifier() is not None:
            loaded_components.append("commit classifier")

        if _get_role_classifier() is not None:
            loaded_components.append("role classifier")

        if get_readme_tone_classifier() is not None:
            loaded_components.append("README tone classifier")

        if not loaded_components:
            message = "ML warmup skipped: summary models are unavailable or disabled."
            logger.info(message)
            return False, message

        message = f"ML warmup complete: {', '.join(loaded_components)} ready."
        logger.info(message)
        return True, message
    except Exception:
        logger.exception("ML warmup failed")
        return False, "ML warmup failed."


def main():
    _init_db()
    _, startup_message = init_system()
    print(startup_message)

    from src.interface.cli.cli import ArtifactMiner
    try:
        ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference

    except KeyboardInterrupt:
        print("Exiting the program...")


if __name__ == '__main__':
    main()
