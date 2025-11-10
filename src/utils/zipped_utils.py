"""
Utility functions for handling zipped files.
"""

import subprocess


def get_os_name() -> str:
    """
    Returns a string representing the current operating system.
    'windows' for Windows, 'macos' for macOS, 'linux' for Linux, 'unknown' otherwise.
    """
    import platform
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    else:
        return 'unknown'


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
