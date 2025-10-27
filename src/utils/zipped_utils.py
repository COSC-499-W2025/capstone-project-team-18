"""
Utility functions for handling zipped files.
"""

import subprocess


def unzip_file(zipped_file: str, extract_to: str) -> None:
    """
    Unzips the given zipped file into the specified directory.
    We can't use zipfile.extractall because it will overide
    the file's creation and modification dates. So instead
    we use the system's cli command to unzip the file.

    Args:
        - zipped_file : str The filepath to the zipped file.
        - extract_to : str The directory to extract files to.
    """

    # TODO: Determine the system's OS and use appropriate unzip command
    subprocess.run(['unzip', '-q', zipped_file, '-d', extract_to], check=True)
