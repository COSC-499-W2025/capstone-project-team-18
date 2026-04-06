import pytest
import src.core.portfolio.builder.concrete_builders as concrete_builders
import src.services.portfolio.generate_update_portfolio_service as portfolio_service
from sqlmodel import Session

from src.utils.errors import KeyNotFoundError
from src.database.api.CRUD.projects import save_project_report, delete_project_report_by_name
from src.database.api.models import PortfolioModel
from src.services.portfolio.generate_update_portfolio_service import (
    generate_and_save_portfolio,
    update_portfolio
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


def test_update_portfolio(mock_engine, prs_db, pr2_updated):
    """Tests that portfolio is updated with information"""

    project_names = ["pr1", "pr2"]
    title = "My Dev Portfolio"

    # Generate inital portoflio
    model = generate_and_save_portfolio(project_names, title)

    assert model.id is not None
    original_update_time = model.last_updated_at
    original_section_ids = {section.section_id for section in model.sections}

    # Delete the project report, and make updated project report
    with Session(prs_db) as session:
        delete_project_report_by_name(session, "pr2")
        save_project_report(session, pr2_updated, None)
        session.commit()

    # Refresh the portfolio with the new information
    updated_model = update_portfolio(model.id)

    assert updated_model is not None
    assert updated_model.id == model.id
    assert updated_model.last_updated_at >= original_update_time

    # Verify all original sections are still present in the updated model
    updated_section_ids = {
        section.section_id for section in updated_model.sections}
    assert original_section_ids.issubset(
        updated_section_ids), "Some original sections are missing after the update"

    # Ensure blocks are present and have content
    for section in updated_model.sections:
        assert len(
            section.blocks) > 0, f"Section '{section.section_id}' has no blocks"

        for block in section.blocks:
            assert block.current_content is not None, f"Block '{block.tag}' is missing content"


def test_generate_portfolio_preserves_existing_project_metadata_when_ml_consent_off(mock_engine, monkeypatch):
    model = generate_and_save_portfolio(["pr1", "pr2"], "Consent Off Portfolio")
    cards_by_name = {card.project_name: card for card in model.project_cards}

    assert cards_by_name["pr1"].tags == ["pytest", "python-backend", "data-modeling"]
    assert cards_by_name["pr1"].activity_metrics == {"avg_commits_per_week": 5.5, "consistency_score": 0.92}
    assert cards_by_name["pr2"].tones == "Creative and accessible"
    assert cards_by_name["pr2"].work_pattern == "burst"
    assert cards_by_name["pr2"].commit_type_distribution == {"feat": 60.0, "fix": 15.0, "style": 25.0}
