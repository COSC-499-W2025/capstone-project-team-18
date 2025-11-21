import os
import pytest
from src.classes.cli import normalize_path


def test_normalize_path_windows_to_unix():
    # Simulate a Windows path on Unix
    input_path = r"C:\Users\TestUser\project.zip"
    expected = os.path.normpath(
        os.path.expanduser("C:/Users/TestUser/project.zip"))
    assert normalize_path(input_path) == expected


def test_normalize_path_unix():
    # Simulate a Unix path
    input_path = "/home/testuser/project.zip"
    expected = os.path.normpath(os.path.expanduser(input_path))
    assert normalize_path(input_path) == expected


def test_normalize_path_home():
    # Simulate a path with ~
    input_path = "~/project.zip"
    expected = os.path.normpath(os.path.expanduser(input_path))
    assert normalize_path(input_path) == expected


def test_normalize_path_mixed_slashes():
    # Simulate a path with mixed slashes
    input_path = r"C:/Users\\TestUser/project.zip"
    expected = os.path.normpath(
        os.path.expanduser("C:/Users/TestUser/project.zip"))
    assert normalize_path(input_path) == expected


def test_normalize_path_empty():
    assert normalize_path("") == ""


def test_windows_path_on_mac():
    # Simulate a Windows path entered on Mac
    input_path = r"C:\\Users\\TestUser\\Documents\\project.zip"
    expected = os.path.normpath(os.path.expanduser(
        "C:/Users/TestUser/Documents/project.zip"))
    assert normalize_path(input_path) == expected


def test_mac_path_on_windows():
    # Simulate a Mac path entered on Windows
    input_path = "/Users/TestUser/Documents/project.zip"
    expected = os.path.normpath(os.path.expanduser(input_path))
    assert normalize_path(input_path) == expected


def test_path_with_dot_and_dotdot():
    # Path with . and ..
    input_path = r"C:/Users/TestUser/../OtherUser/./project.zip"
    expected = os.path.normpath(os.path.expanduser(
        "C:/Users/TestUser/../OtherUser/./project.zip"))
    assert normalize_path(input_path) == expected


def test_path_with_trailing_slash():
    # Path with trailing slash
    input_path = r"C:/Users/TestUser/"
    expected = os.path.normpath(os.path.expanduser("C:/Users/TestUser/"))
    assert normalize_path(input_path) == expected

def test_windows_path_on_mac():
    # Simulate a Windows path entered on Mac
    import sys
    if sys.platform == 'darwin':
        input_path = r"C:\\Users\\TestUser\\Desktop\\project.zip"
        expected = os.path.normpath(os.path.expanduser("/Users/TestUser/Desktop/project.zip"))
        assert normalize_path(input_path) == expected
        # Also test with forward slashes
        input_path2 = "C:/Users/TestUser/Desktop/project.zip"
        assert normalize_path(input_path2) == expected
    else:
        # On non-Mac platforms, normalization should use OS separator
        input_path = r"C:\\Users\\TestUser\\Desktop\\project.zip"
        expected = os.path.normpath(os.path.expanduser(input_path.replace('\\', os.sep).replace('/', os.sep)))
        assert normalize_path(input_path) == expected
