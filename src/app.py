"""
The entry point for the ArtifactMiner program.
"""

if __name__ == '__main__':
    from src.classes.cli import ArtifactMiner

    try:
        ArtifactMiner().cmdloop()  # create an ArtifactMiner obj w/out a reference

    except KeyboardInterrupt:
        print("Exiting the program...")
