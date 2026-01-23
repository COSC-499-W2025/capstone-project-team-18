"""
The entry point for the ArtifactMiner program.
"""

from src.infrastructure.database.utils.db_migrate import run_migrations
from src.infrastructure.log.logging import clear_logs


def main():
    clear_logs()
    run_migrations()

    from src.interface.cli.cli import ArtifactMiner
    try:
        ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference

    except KeyboardInterrupt:
        print("Exiting the program...")


if __name__ == '__main__':
    main()
