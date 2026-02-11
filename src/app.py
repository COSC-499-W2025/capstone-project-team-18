"""
The entry point for the ArtifactMiner program.
"""

import os

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def _init_db() -> None:
    """
    Initialize database schema at startup.

    Prefer legacy migration hook when present; otherwise fall back to SQLModel
    table creation used by the API/service startup path.
    """
    try:
        from src.database.utils.db_migrate import run_migrations
        run_migrations()
        return
    except ModuleNotFoundError:
        pass

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
        from src.core.ML.models.llama_cpp_runtime import (
            llama_cpp_enabled,
            resolve_llama_cpp_model_path,
            warmup_llama_cpp_model,
        )

        loaded_components: list[str] = []

        if llama_cpp_enabled() and ml_extraction_allowed():
            signature_path = resolve_llama_cpp_model_path("ARTIFACT_MINER_LLAMA_CPP_SIGNATURE_MODEL_PATH")
            project_path = resolve_llama_cpp_model_path("ARTIFACT_MINER_LLAMA_CPP_PROJECT_MODEL_PATH")

            if not signature_path:
                logger.warning("llama-cpp enabled but no signature GGUF model path could be resolved")
            if not project_path:
                logger.warning("llama-cpp enabled but no project-summary GGUF model path could be resolved")

            if (
                signature_path
                and
                os.environ.get("ARTIFACT_MINER_DISABLE_SIGNATURE_MODEL") != "1"
                and warmup_llama_cpp_model(signature_path)
            ):
                loaded_components.append("signature summary (llama-cpp)")

            if project_path and project_path == signature_path:
                if (
                    os.environ.get("ARTIFACT_MINER_DISABLE_PROJECT_SUMMARY_MODEL") != "1"
                    and "signature summary (llama-cpp)" in loaded_components
                ):
                    loaded_components.append("project summary (llama-cpp)")
                elif (
                    os.environ.get("ARTIFACT_MINER_DISABLE_PROJECT_SUMMARY_MODEL") != "1"
                    and warmup_llama_cpp_model(project_path)
                ):
                    loaded_components.append("project summary (llama-cpp)")
            elif (
                project_path
                and
                os.environ.get("ARTIFACT_MINER_DISABLE_PROJECT_SUMMARY_MODEL") != "1"
                and warmup_llama_cpp_model(project_path)
            ):
                loaded_components.append("project summary (llama-cpp)")
        else:
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
