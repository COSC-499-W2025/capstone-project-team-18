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
    We can't use zipfile.extractall because it will override
    the file's creation and modification dates. So instead
    we use the system's cli command to unzip the file.
    Args:
        - zipped_file : str The filepath to the zipped file.
        - extract_to : str The directory to extract files to.
    """

    # TODO: Determine the system's OS and use appropriate unzip command
    import os
    import zipfile
    import tarfile
    import shutil
    os_name = get_os_name()
    try:
        import py7zr
    except ImportError:
        py7zr = None
    ext = os.path.splitext(zipped_file)[1].lower()
    # Handle .tar.gz and .gz
    if zipped_file.endswith('.tar.gz'):
        if os_name == 'windows':
            # Use tar via cmd (Windows 10+ has tar)
            subprocess.run(['tar', '-xzf', zipped_file,
                           '-C', extract_to], check=True)
        else:
            subprocess.run(['tar', '-xzf', zipped_file,
                           '-C', extract_to], check=True)
    elif ext == '.gz':
        if os_name == 'windows':
            # Use tar or 7z for .gz on Windows
            try:
                subprocess.run(['tar', '-xzf', zipped_file,
                               '-C', extract_to], check=True)
            except Exception:
                subprocess.run(
                    ['7z', 'x', zipped_file, f'-o{extract_to}'], check=True)
        else:
            subprocess.run(['tar', '-xzf', zipped_file,
                           '-C', extract_to], check=True)
    elif ext == '.zip':
        if os_name == 'windows':
            # Use PowerShell Expand-Archive
            try:
                subprocess.run([
                    'powershell', '-Command',
                    f"Expand-Archive -Path '{zipped_file}' -DestinationPath '{extract_to}' -Force"
                ], check=True)
            except Exception:
                # Fallback to Python zipfile
                with zipfile.ZipFile(zipped_file, 'r') as zipf:
                    zipf.extractall(extract_to)
        else:
            try:
                subprocess.run(['unzip', '-q', zipped_file,
                               '-d', extract_to], check=True)
            except Exception:
                # Fallback to Python zipfile
                with zipfile.ZipFile(zipped_file, 'r') as zipf:
                    zipf.extractall(extract_to)
    elif ext == '.7z':
        if os_name == 'windows' or os_name in ('linux', 'macos'):
            try:
                subprocess.run(
                    ['7z', 'x', zipped_file, f'-o{extract_to}'], check=True)
            except Exception:
                if py7zr is not None:
                    with py7zr.SevenZipFile(zipped_file, 'r') as archive:
                        archive.extractall(path=extract_to)
                else:
                    raise ValueError(
                        "py7zr not installed and 7z extraction failed.")
        else:
            raise ValueError(f"Unsupported OS for .7z extraction: {os_name}")
    else:
        raise ValueError(f"Unsupported archive format: {zipped_file}")
