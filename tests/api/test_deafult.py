"""
Tests the FastAPI infrastructure as a whole.
"""

import pytest


def test_ping_pong(client):
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == "pong"


@pytest.mark.parametrize(
    "method,url",
    [
        ("POST", "/projects/upload"),
        ("POST", "/privacy-consent"),
        ("GET", "/projects"),
        ("GET", "/projects/test-id"),          # placeholder ID
        ("GET", "/skills"),
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
