"""
Tests for the project retrieval endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.services.project.retrieve_project_service import ProjectResponse, AllProjectsResponse
from src.database.models.project_report_table import ProjectReportTable


@pytest.fixture
def mock_project_data():
    """Mock project data for testing"""
    return {
        "id": 1,
        "project_name": "Test Project",
        "project_path": "/path/to/test/project",
        "project_start_date": datetime(2024, 1, 1),
        "project_end_date": datetime(2024, 12, 31),
        "project_skills_demonstrated": [
            {"skill_name": "Web Development", "weight": 0.7},
            {"skill_name": "Database", "weight": 0.3}
        ],
        "coding_language_ratio": {"Python": 0.8, "JavaScript": 0.2},
        "total_project_lines": 5000,
    }


@pytest.fixture
def mock_project_row(mock_project_data):
    """Create a mock ProjectReportTable row"""
    mock_row = MagicMock(spec=ProjectReportTable)
    mock_row.id = mock_project_data["id"]
    mock_row.project_name = mock_project_data["project_name"]
    mock_row.project_path = mock_project_data["project_path"]
    mock_row.project_start_date = mock_project_data["project_start_date"]
    mock_row.project_end_date = mock_project_data["project_end_date"]
    mock_row.project_skills_demonstrated = mock_project_data["project_skills_demonstrated"]
    mock_row.coding_language_ratio = mock_project_data["coding_language_ratio"]
    mock_row.total_project_lines = mock_project_data["total_project_lines"]
    return mock_row


class TestGetAllProjects:
    """Tests for GET /projects endpoint"""

    def test_get_all_projects_empty_database(self, client):
        """Test GET /projects when database is empty"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.all.return_value = []

            response = client.get("/projects")

            assert response.status_code == 200
            data = response.json()
            assert "projects" in data
            assert data["projects"] == []

    def test_get_all_projects_with_data(self, client, mock_project_row):
        """Test GET /projects returns project data"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.all.return_value = [mock_project_row]

            response = client.get("/projects")

            assert response.status_code == 200
            data = response.json()
            assert "projects" in data
            assert len(data["projects"]) == 1
            assert data["projects"][0]["id"] == 1
            assert data["projects"][0]["project_name"] == "Test Project"

    def test_get_all_projects_multiple_projects(self, client, mock_project_row):
        """Test GET /projects with multiple projects"""
        mock_project_2 = MagicMock(spec=ProjectReportTable)
        mock_project_2.id = 2
        mock_project_2.project_name = "Test Project 2"
        mock_project_2.project_path = "/path/to/test/project2"
        mock_project_2.project_start_date = datetime(2024, 6, 1)
        mock_project_2.project_end_date = datetime(2024, 12, 31)

        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.all.return_value = [
                mock_project_row, mock_project_2
            ]

            response = client.get("/projects")

            assert response.status_code == 200
            data = response.json()
            assert len(data["projects"]) == 2
            assert data["projects"][0]["id"] == 1
            assert data["projects"][1]["id"] == 2

    def test_get_all_projects_response_structure(self, client, mock_project_row):
        """Test that the response has the correct structure"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.all.return_value = [mock_project_row]

            response = client.get("/projects")

            assert response.status_code == 200
            data = response.json()

            # Check top-level structure
            assert "projects" in data

            # Check project structure
            project = data["projects"][0]
            assert "id" in project
            assert "project_name" in project
            assert "project_path" in project
            assert "date_created" in project
            assert "date_updated" in project
            assert "statistics" in project


class TestGetProjectById:
    """Tests for GET /projects/{project_id} endpoint"""

    def test_get_project_by_id_success(self, client, mock_project_row):
        """Test GET /projects/{id} returns specific project"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_project_row

            response = client.get("/projects/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["project_name"] == "Test Project"
            assert data["project_path"] == "/path/to/test/project"

    def test_get_project_by_id_not_found(self, client):
        """Test GET /projects/{id} returns 404 for non-existent project"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None

            response = client.get("/projects/999")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert data["detail"] == "Project not found"

    def test_get_project_by_id_includes_statistics(self, client, mock_project_row):
        """Test that project includes statistics data"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_project_row

            response = client.get("/projects/1")

            assert response.status_code == 200
            data = response.json()
            assert "statistics" in data
            assert isinstance(data["statistics"], dict)

    def test_get_project_by_id_response_structure(self, client, mock_project_row):
        """Test that single project response has correct structure"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_project_row

            response = client.get("/projects/1")

            assert response.status_code == 200
            data = response.json()

            # Check required fields
            assert "id" in data
            assert "project_name" in data
            assert "project_path" in data
            assert "date_created" in data
            assert "date_updated" in data
            assert "statistics" in data

            # Check types
            assert isinstance(data["id"], int)
            assert isinstance(data["project_name"], str)
            assert isinstance(data["project_path"], str)
            assert isinstance(data["statistics"], dict)

    def test_get_project_handles_missing_optional_fields(self, client):
        """Test that project handles None values for optional fields"""
        mock_row = MagicMock(spec=ProjectReportTable)
        mock_row.id = 1
        mock_row.project_name = None
        mock_row.project_path = None
        mock_row.project_start_date = None
        mock_row.project_end_date = None

        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_row

            response = client.get("/projects/1")

            assert response.status_code == 200
            data = response.json()
            assert data["project_name"] == "Unknown Project"
            assert data["project_path"] == "Unknown Path"
            assert data["date_created"] is None
            assert data["date_updated"] is None


class TestProjectResponseModels:
    """Tests for Pydantic response models"""

    def test_project_response_model_validation(self):
        """Test ProjectResponse model validates correctly"""
        valid_data = {
            "id": 1,
            "project_name": "Test",
            "project_path": "/path",
            "date_created": datetime.now(),
            "date_updated": datetime.now(),
            "statistics": {"key": "value"}
        }

        response = ProjectResponse(**valid_data)
        assert response.id == 1
        assert response.project_name == "Test"
        assert response.statistics == {"key": "value"}

    def test_all_projects_response_model_validation(self):
        """Test AllProjectsResponse model validates correctly"""
        project = ProjectResponse(
            id=1,
            project_name="Test",
            project_path="/path",
            statistics={}
        )

        response = AllProjectsResponse(projects=[project])
        assert len(response.projects) == 1
        assert response.projects[0].id == 1

    def test_project_response_handles_optional_dates(self):
        """Test ProjectResponse handles None for optional date fields"""
        data = {
            "id": 1,
            "project_name": "Test",
            "project_path": "/path",
            "date_created": None,
            "date_updated": None,
            "statistics": {}
        }

        response = ProjectResponse(**data)
        assert response.date_created is None
        assert response.date_updated is None


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_get_project_invalid_id_type(self, client):
        """Test GET /projects/{id} with invalid ID type"""
        response = client.get("/projects/invalid-id")

        # FastAPI validation should catch this
        assert response.status_code == 422

    def test_get_project_negative_id(self, client):
        """Test GET /projects/{id} with negative ID"""
        with patch('src.services.project.retrieve_project_service.Session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None

            response = client.get("/projects/-1")

            assert response.status_code == 404