import os
import shutil
import tempfile
import zipfile
import tarfile
try:
    import py7zr
except ImportError:
    py7zr = None
from utils.zipped_utils import unzip_file


def create_test_zip(zip_path, filename, content):
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        with tempfile.NamedTemporaryFile('w', delete=False) as tmpf:
            tmpf.write(content)
            tmpf.flush()
            zipf.write(tmpf.name, arcname=filename)
        os.unlink(tmpf.name)


def create_test_tar_gz(tar_gz_path, filename, content):
    with tempfile.NamedTemporaryFile('w', delete=False) as tmpf:
        tmpf.write(content)
        tmpf.flush()
        with tarfile.open(tar_gz_path, 'w:gz') as tar:
            tar.add(tmpf.name, arcname=filename)
        os.unlink(tmpf.name)


def create_test_7z(sevenz_path, filename, content):
    if py7zr is None:
        return False
    with tempfile.NamedTemporaryFile('w', delete=False) as tmpf:
        tmpf.write(content)
        tmpf.flush()
        with py7zr.SevenZipFile(sevenz_path, 'w') as archive:
            archive.write(tmpf.name, arcname=filename)
        os.unlink(tmpf.name)
    return True


def test_unzip_file():
    test_cases = [
        ('test_unzip.zip', 'hello_zip.txt', 'Hello from zip!', create_test_zip),
        ('test_unzip.tar.gz', 'hello_targz.txt',
         'Hello from tar.gz!', create_test_tar_gz),
    ]
    if py7zr is not None:
        test_cases.append(('test_unzip.7z', 'hello_7z.txt',
                          'Hello from 7z!', create_test_7z))
    extract_dir = 'test_unzip_extract'
    for archive, fname, content, creator in test_cases:
        if os.path.exists(archive):
            os.remove(archive)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        creator(archive, fname, content)
        os.makedirs(extract_dir, exist_ok=True)  # Ensure extraction dir exists
        unzip_file(archive, extract_dir)
        extracted_file = os.path.join(extract_dir, fname)
        assert os.path.exists(
            extracted_file), f"{extracted_file} was not extracted!"
        with open(extracted_file, 'r') as f:
            assert f.read(
            ) == content, f"Extracted file content does not match for {archive}!"
        print(f"Unzip test passed for {archive}")


if __name__ == "__main__":
    test_unzip_file()
