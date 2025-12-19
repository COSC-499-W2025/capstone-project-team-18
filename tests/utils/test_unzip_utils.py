"""
Unit tests for unzip_file function in zipped_utils module.
"""
import zipfile
import tarfile
import py7zr
from src.utils.zipped_utils import unzip_file


def test_unzip_file_zip(tmp_path):
    """
    Test unzipping a .zip file.
    """

    zip_path = tmp_path / "test.zip"
    extract_dir = tmp_path / "extracted_zip"
    extract_dir.mkdir()

    # Create a zip file
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.writestr('file1.txt', 'This is file 1')
        zipf.writestr('file2.txt', 'This is file 2')

    unzip_file(str(zip_path), str(extract_dir))

    assert (extract_dir / 'file1.txt').exists()
    assert (extract_dir / 'file2.txt').exists()


def test_unzip_file_tar_gz(tmp_path):
    """
    Test unzipping a .tar.gz file.
    """
    tar_gz_path = tmp_path / "test.tar.gz"
    extract_dir = tmp_path / "extracted_tar_gz"
    extract_dir.mkdir()

    # Create a tar.gz file
    with tarfile.open(tar_gz_path, 'w:gz') as tar:
        file1 = tmp_path / 'file1.txt'
        file2 = tmp_path / 'file2.txt'
        file1.write_text('This is file 1')
        file2.write_text('This is file 2')
        tar.add(file1, arcname='file1.txt')
        tar.add(file2, arcname='file2.txt')

    unzip_file(str(tar_gz_path), str(extract_dir))

    assert (extract_dir / 'file1.txt').exists()
    assert (extract_dir / 'file2.txt').exists()


def test_unzip_file_7z(tmp_path):
    """
    Test unzipping a .7z file.
    """

    seven_z_path = tmp_path / "test.7z"
    extract_dir = tmp_path / "extracted_7z"
    extract_dir.mkdir()

    # Create a 7z file
    with py7zr.SevenZipFile(seven_z_path, 'w') as archive:
        file1 = tmp_path / 'file1.txt'
        file2 = tmp_path / 'file2.txt'
        file1.write_text('This is file 1')
        file2.write_text('This is file 2')
        archive.write(file1, arcname='file1.txt')
        archive.write(file2, arcname='file2.txt')

    unzip_file(str(seven_z_path), str(extract_dir))

    assert (extract_dir / 'file1.txt').exists()
    assert (extract_dir / 'file2.txt').exists()
