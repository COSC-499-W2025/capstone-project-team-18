"""
Integration tests for the project image upload and retrieval endpoints.
"""

import pytest
from sqlmodel import Session
from datetime import datetime
from unittest.mock import patch

from src.database.api.models import ProjectReportModel

# --- Fixtures ---


@pytest.fixture
def seeded_project(blank_db):
    """
    Seeds the test database with a baseline ProjectReportModel.
    We request the `blank_db` fixture directly to interact with the database.
    """
    with Session(blank_db) as session:
        project = ProjectReportModel(
            project_name="TestProject",
            statistic={"lines_of_code": 100},
            created_at=datetime.now(),
            last_updated=datetime.now(),
            # image_data defaults to None
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # Return the project name or model so tests can use it
        return project


@pytest.fixture
def seeded_project_with_image(blank_db, seeded_project):
    """
    Adds dummy image bytes to the baseline seeded project.
    """
    with Session(blank_db) as session:
        # Fetch the project we just seeded
        project = session.get(ProjectReportModel, seeded_project.project_name)
        project.image_data = b"existing dummy image bytes"
        session.add(project)
        session.commit()
        session.refresh(project)
        return project


# --- Tests for POST /projects/{project_name}/image ---

def test_upload_project_image_success(client, blank_db, seeded_project):
    """Test successfully uploading an image for an existing project and saving to DB"""

    file_data = {
        "file": ("thumbnail.png", b"new fake image bytes", "image/png")
    }

    # Hit the endpoint
    response = client.post(
        f"/projects/{seeded_project.project_name}/image", files=file_data)

    # Validate response
    assert response.status_code == 200
    assert "successfully assigned" in response.json()["message"]

    # Verify the database was actually updated
    with Session(blank_db) as session:
        updated_project = session.get(
            ProjectReportModel, seeded_project.project_name)
        assert updated_project.image_data == b"new fake image bytes"
        # Ensure last_updated was modified
        assert updated_project.last_updated > seeded_project.last_updated


def test_upload_project_image_not_found(client):
    """Test uploading an image to a nonexistent project returns 404"""
    file_data = {
        "file": ("thumbnail.png", b"fake image bytes", "image/png")
    }

    response = client.post(
        "/projects/NonExistentProject/image", files=file_data)

    assert response.status_code == 404
    assert "No project report named NonExistentProject" in response.json()[
        "message"]


def test_upload_project_image_invalid_type(client, seeded_project):
    """Test uploading a non-image file returns a 400 bad request"""
    # Send a PDF instead of an image to trigger the validation check
    file_data = {
        "file": ("document.pdf", b"fake pdf bytes", "application/pdf")
    }

    response = client.post(
        f"/projects/{seeded_project.project_name}/image", files=file_data)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_project_image_db_failure(client, seeded_project):
    """Test that a database failure during upload results in a 500 and a rollback"""
    file_data = {
        "file": ("thumbnail.png", b"fake image bytes", "image/png")
    }

    # We still patch the commit here solely to force an exception
    # and ensure the endpoint catches it gracefully.
    with patch('sqlmodel.Session.commit', side_effect=Exception("DB connection lost")):
        response = client.post(
            f"/projects/{seeded_project.project_name}/image", files=file_data)

        assert response.status_code == 500
        assert "Failed to upload image" in response.json()["message"]


def test_upload_project_image_sneaky_extension(client, seeded_project):
    """
    Test that a file with an image extension but a non-image content-type is rejected.
    This ensures we validate the MIME type and aren't fooled by the filename.
    """
    # The filename ends in .png, but the client explicitly declares it as text/plain
    file_data = {
        "file": ("sneaky.png", b"this is actually just text", "text/plain")
    }

    response = client.post("/projects/TestProject/image", files=file_data)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


# --- Tests for DELETE /projects/{project_name}/image ---

def test_delete_project_image_success(client, blank_db, seeded_project_with_image):
    """Successfully removing an image returns 200 and clears image_data in DB."""
    r = client.delete(f"/projects/{seeded_project_with_image.project_name}/image")

    assert r.status_code == 200
    assert "successfully removed" in r.json()["message"]

    with Session(blank_db) as session:
        proj = session.get(ProjectReportModel, seeded_project_with_image.project_name)
        assert proj.image_data is None


def test_delete_project_image_not_found(client, blank_db):
    """Deleting an image from a non-existent project returns 404."""
    r = client.delete("/projects/ghost-project/image")
    assert r.status_code == 404
    assert r.json()["error_code"] == "PROJECT_NOT_FOUND"


def test_delete_project_image_already_null_is_ok(client, blank_db, seeded_project):
    """Deleting when image is already None still returns 200 (idempotent)."""
    r = client.delete(f"/projects/{seeded_project.project_name}/image")
    assert r.status_code == 200


def test_delete_project_image_db_failure(client, seeded_project):
    """A commit failure during delete returns 500."""
    with patch('sqlmodel.Session.commit', side_effect=Exception("disk full")):
        r = client.delete(f"/projects/{seeded_project.project_name}/image")
    assert r.status_code == 500
    assert r.json()["error_code"] == "DATABASE_OPERATION_FAILED"
