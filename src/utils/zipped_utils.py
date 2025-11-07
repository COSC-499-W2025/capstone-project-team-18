
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


"""
Utility functions for handling zipped files.
"""
