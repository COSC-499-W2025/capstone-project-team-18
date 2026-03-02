"""
Utility functions for handling zipped files.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import py7zr

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

IS_WINDOWS = os.name == "nt"


def _has_tool(tool: str) -> bool:
    return shutil.which(tool) is not None


def _run(cmd: list[str]) -> None:
    """Run a subprocess command with logging."""
    logger.debug("Running command: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def unzip_file(zipped_file: str, extract_to: str) -> None:
    """
    Unzips the given archive into the specified directory.

    We avoid zipfile.extractall by default because it does not preserve
    original timestamps. Instead, we prefer native CLI tools and fall
    back to Python libraries when necessary.

    :param zipped_file: String path to the zipped file
    :type zipped_file: str
    :param extract_to: String path to the directory to unzip into
    :type extract_to: str
    """
    ext = os.path.splitext(zipped_file)[1].lower()

    try:
        if zipped_file.endswith(".tar.gz") or ext == ".gz":
            _extract_tar(zipped_file, extract_to)

        elif ext == ".zip":
            _extract_zip(zipped_file, extract_to)

        elif ext == ".7z":
            _extract_7z(zipped_file, extract_to)

        else:
            raise ValueError(f"Unsupported archive format: {zipped_file}")

    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to extract archive: {zipped_file}"
        ) from exc


def _extract_tar(zipped_file: str, extract_to: str) -> None:
    if _has_tool("tar"):
        try:
            _run(["tar", "-xzf", zipped_file, "-C", extract_to])
            return
        except subprocess.CalledProcessError:
            logger.warning("tar failed")

    if IS_WINDOWS and _has_tool("7z"):
        _run(["7z", "x", zipped_file, f"-o{extract_to}"])
        return

    raise RuntimeError("No available tool to extract tar archive")


def _extract_zip(zipped_file: str, extract_to: str) -> None:
    """Extract .zip archives."""
    try:
        if IS_WINDOWS:
            _run([
                "powershell",
                "-Command",
                f"Expand-Archive -Path '{zipped_file}' "
                f"-DestinationPath '{extract_to}' -Force"
            ])
        else:
            _run(["unzip", "-q", zipped_file, "-d", extract_to])

    except subprocess.CalledProcessError:
        logger.warning("CLI unzip failed, falling back to zipfile")
        with zipfile.ZipFile(zipped_file, "r") as zipf:
            zipf.extractall(extract_to)


def _extract_7z(zipped_file: str, extract_to: str) -> None:
    """Extract .7z archives."""
    if _has_tool("7z"):
        try:
            _run(["7z", "x", zipped_file, f"-o{extract_to}"])
            return
        except subprocess.CalledProcessError:
            logger.warning("7z CLI failed, falling back to py7zr")

    logger.info("Using py7zr fallback for .7z extraction")
    with py7zr.SevenZipFile(zipped_file, "r") as archive:
        archive.extractall(path=extract_to)


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


def is_valid_filepath_to_zip(filepath: str) -> int:
    """
    Helper function to validate the provided filepath.
    A valid filepath must exist and be a zipped file.

    Int code returns:
    0 - valid filepath to a zip file
    1 - invalid filepath
    2 - filepath does not point to a zip file
    3 - filepath does not exist
    """

    if not os.path.exists(filepath):
        return 3
    if not os.path.isfile(filepath):
        return 1
    valid_exts = ('.zip', '.tar.gz', '.gz', '.7z')
    if not any(filepath.endswith(ext) for ext in valid_exts):
        return 2
    return 0


