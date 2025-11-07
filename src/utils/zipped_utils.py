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
    import os
    import zipfile
    import tarfile
    import shutil
    try:
        import py7zr
    except ImportError:
        py7zr = None
    ext = os.path.splitext(zipped_file)[1].lower()
    # Handle .tar.gz and .gz
    if zipped_file.endswith('.tar.gz'):
        with tarfile.open(zipped_file, 'r:gz') as tar:
            tar.extractall(path=extract_to, filter=tarfile.data_filter)
    elif ext == '.gz':
        # Assume it's a single file compressed with gzip
        import gzip
        base = os.path.basename(zipped_file)
        out_file = os.path.join(extract_to, base[:-3])
        os.makedirs(extract_to, exist_ok=True)
        with gzip.open(zipped_file, 'rb') as f_in, open(out_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    elif ext == '.zip':
        try:
            with zipfile.ZipFile(zipped_file, 'r') as zipf:
                zipf.extractall(extract_to)
        except Exception:
            # Fallback to system unzip if Python extraction fails
            subprocess.run(['unzip', '-q', zipped_file,
                           '-d', extract_to], check=True)
    elif ext == '.7z' and py7zr is not None:
        with py7zr.SevenZipFile(zipped_file, 'r') as archive:
            archive.extractall(path=extract_to)
    elif ext == '.7z':
        # Fallback to system 7z if available
        subprocess.run(['7z', 'x', zipped_file, f'-o{extract_to}'], check=True)
    else:
        raise ValueError(f"Unsupported archive format: {zipped_file}")
