"""
The entry point for the ArtifactMiner program.
"""

from src.database import get_engine
from sqlmodel import SQLModel


def main():

    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    from src.interface.cli.cli import ArtifactMiner
    try:
        ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference

    except KeyboardInterrupt:
        print("Exiting the program...")


if __name__ == '__main__':
    main()
