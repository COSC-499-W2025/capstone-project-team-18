import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.interface.api.routers.util import get_session


from src.interface.api.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True, scope="function")
def mock_engine(client, blank_db):
    def fake_get_session():
        with Session(blank_db) as session:
            yield session

    client.app.dependency_overrides[get_session] = fake_get_session
    yield
    client.app.dependency_overrides.clear()
