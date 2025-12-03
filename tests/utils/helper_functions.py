'''
Global helper functions for all test files
'''
from pathlib import Path


def get_temp_file(filename: str, content: str, path: Path):
    '''
    Create a temporary file with given arguments

    Args
        filename (str): The name of the file (e.g., 'app.py')
        content (str): The content within the file
        path (Path): The path to the file
    '''
    file = path / filename
    file.write_text(content)
    return file


def get_temp_local_dir(dir_name: str, path: Path):
    '''
    Create a temporary empty directory

    Args
        dir_name (str): The name of the directory
        path (Path): The path to the directory
    '''
    empty_dir = path / dir_name
    empty_dir.mkdir()
    return empty_dir
