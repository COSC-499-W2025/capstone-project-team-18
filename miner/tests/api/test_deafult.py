"""
Tests the FastAPI infrastructure as a whole.
"""

import pytest
from sqlmodel import Session

from src.interface.api.routers.util import get_session


@pytest.fixture(autouse=True, scope="function")
def mock_engine(client, blank_db):
    def fake_get_session():
        with Session(blank_db) as session:
            yield session

    client.app.dependency_overrides[get_session] = fake_get_session
    yield
    client.app.dependency_overrides.clear()


def test_ping_pong(client):
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == "pong"


@pytest.mark.parametrize(
    "method,url",
    [
        ("POST", "/projects/upload"),
        ("GET", "/projects"),
        ("GET", "/projects/test-id"),
        ("GET", "/resume/test-id"),
        ("POST", "/resume/generate"),
        ("POST", "/resume/test-id/edit"),
        ("GET", "/portfolio/test-id"),
        ("POST", "/portfolio/generate"),
        ("POST", "/portfolio/test-id/edit"),
    ]
)
def test_routes_exist(client, method, url):
    """
    Checks that the route exists and responds with a status code < 500.
    """
    response = client.request(method, url)
    assert response.status_code < 500  # ensures endpoint is reachable
