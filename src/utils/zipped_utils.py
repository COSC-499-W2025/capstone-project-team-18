"""
Utility functions for handling zipped files.
"""

import subprocess
import tempfile
import os
import tempfile

from src.utils.log.logging import get_logger

logger = get_logger(__name__)


def get_os_name() -> str:
    """
    Returns a string representing the current operating system.
    Tries to use the HOST_OS environment variable (set by the dev container) if available.
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
    import py7zr
    os_name = get_os_name()
    logger.info("This system is %s", os_name)

    ext = os.path.splitext(zipped_file)[1].lower()
    # Combine .tar.gz and .gz handling since both use tar extraction
    if zipped_file.endswith('.tar.gz') or ext == '.gz':
        try:
            subprocess.run(['tar', '-xzf', zipped_file,
                           '-C', extract_to], check=True)
        except subprocess.CalledProcessError:
            # Fallback: On Windows, try 7z if tar fails for .gz
            if os_name == 'windows' and ext == '.gz':
                subprocess.run(
                    ['7z', 'x', zipped_file, f'-o{extract_to}'], check=True)
            else:
                raise
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
                with py7zr.SevenZipFile(zipped_file, 'r') as archive:
                    archive.extractall(path=extract_to)
        else:
            raise ValueError(f"Unsupported OS for .7z extraction: {os_name}")
    else:
        raise ValueError(f"Unsupported archive format: {zipped_file}")


def unzip_file_bytes(
    zipped_bytes: bytes,
    zipped_format: str,
    unzipped_dir: str
) -> None:
    """
    Unzips zipped bytes in given format into the given directory.

    :param zipped_bytes: The bytes of a zipped file
    :type zipped_bytes: bytes
    :param zipped_format: The format of the zipped file (.zip, .7z, .gz)
    :type zipped_format: str
    :param unzipped_dir: A filepath to the directory where the files should be unzipped
    :type unzipped_dir: str
    """

    # Normalize format
    if not zipped_format.startswith('.'):
        logger.warning("unzip_file_bytes had to normalize the zipped_format")
        zipped_format = f".{zipped_format}"

    temp_file_path = None

    try:
        # Create temporary file with the byte
        with tempfile.NamedTemporaryFile(delete=False, suffix=zipped_format) as tmp:
            tmp.write(zipped_bytes)
            tmp.flush()
            temp_file_path = tmp.name

        logger.info(
            "Extracting archive bytes using temporary file: %s",
            temp_file_path
        )

        unzip_file(temp_file_path, unzipped_dir)

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                logger.warning(
                    "Failed to remove temporary archive file: %s",
                    temp_file_path
                )
