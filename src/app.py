"""
The entry point for the ArtifactMiner program.
"""

from src.database.utils.db_migrate import run_migrations

db_url = "sqlite:///src/database/data.db"


def main():
    run_migrations(db_url)

    from src.interface.cli.cli import ArtifactMiner
    try:
        ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference

    except KeyboardInterrupt:
        print("Exiting the program...")


if __name__ == '__main__':
    main()
