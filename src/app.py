"""
The entry point for the ArtifactMiner program.
"""

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def init_system() -> tuple[bool, str]:
    """
    This function does any setup and warmup tasks that are needed for a cold
    session start for the system. This includes both database configuration
    and ML warm-up.
    """
    # Setup db (handled separately)
    # Setup ML warm-up
    try:
        from src.core.ML.models.contribution_analysis.summary_generator import _load_model

        model, tokenizer = _load_model()
        if model is None or tokenizer is None:
            message = "Summary model not available or disabled."
            logger.info(message)
            return False, message

        message = "Summary model loaded and ready."
        logger.info(message)
        return True, message
    except Exception:
        logger.exception("Summary model warmup failed")
        return False, "Summary model warmup failed."


def main():
    _, startup_message = init_system()
    print(startup_message)

    from src.interface.cli.cli import ArtifactMiner
    try:
        ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference

    except KeyboardInterrupt:
        print("Exiting the program...")


if __name__ == '__main__':
    main()
