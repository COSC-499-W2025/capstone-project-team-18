import pytest
from fastapi.testclient import TestClient

from src.interface.api.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
