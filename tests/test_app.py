"""
This pytest file will just simply test that the app runs without errors.
More detailed tests will be in their respective modules.
"""

import pytest
from src.app import start_miner


def test_app_runs():
    """
    Test that the main app function runs without errors.
    """
    # Use a sample zipped file path for testing
    sample_zipped_file = "./tests/resources/mac_projects.zip"
    sample_email = "bob@example.com"

    try:
        start_miner(sample_zipped_file, sample_email)
    except Exception as e:
        pytest.fail(f"start_miner raised an exception: {e}")
