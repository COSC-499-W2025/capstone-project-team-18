from utils.zipped_utils import get_os_name


def test_host_os():
    import os as _os
    host_os = _os.environ.get("HOST_OS", "not set")


if __name__ == "__main__":
    test_host_os()
