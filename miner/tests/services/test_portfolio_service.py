import pytest
from sqlmodel import Session

from src.utils.errors import KeyNotFoundError
from src.database.api.models import PortfolioModel
from src.services.portfolio.generate_update_portfolio_service import (
    generate_and_save_portfolio
)


@pytest.fixture(autouse=True, scope="function")
def mock_engine(monkeypatch, prs_db):
    """
    Tells start_miner to use our fake_get_engine function
    rather than the real get_engine() function
    """

    def fake_get_engine():
        return prs_db

    monkeypatch.setattr(
        "src.services.portfolio.generate_update_portfolio_service.get_engine", fake_get_engine)
    yield prs_db


def test_generate_and_save_portfolio_success(mock_engine, prs_db):
    """Test that a portfolio is created correctly from existing project reports."""
    project_names = ["pr1", "pr2"]
    title = "My Dev Portfolio"

    model = generate_and_save_portfolio(project_names, title)

    assert isinstance(model, PortfolioModel)
    assert model.title == title
    assert model is not None
    assert model.project_ids_include == project_names

    with Session(prs_db) as session:
        saved = session.get(PortfolioModel, model.id)
        assert saved is not None
        assert len(saved.sections) > 0


def test_generate_portfolio_with_missing_project_names(mock_engine):
    """Test that it raises KeyNotFoundError if a project name doesn't exist."""
    with pytest.raises(KeyNotFoundError) as excinfo:
        generate_and_save_portfolio(["NonExistent"], "Title")
        assert "No project report with key NonExistent" in str(excinfo.value)
