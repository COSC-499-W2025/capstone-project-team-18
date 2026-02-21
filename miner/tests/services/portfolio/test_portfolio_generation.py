import pytest
from unittest.mock import patch
from sqlmodel import Session

from src.core.portfolio.portfolio import Portfolio
from src.core.portfolio.sections.block.block_content import TextBlock
from src.database.api.CRUD.portfolio import load_portfolio, get_portfolio_block, save_portfolio
from src.services.portfolio.generate_update_portfolio_service import (
    generate_and_save_portfolio,
    update_portfolio,
    merge_portfolios
)


def test_generate_and_save_portfolio_flow(blank_db, mock_project_reports):
    """
    Test that project names are converted into a saved PortfolioModel
    with the correct sections.
    """
    # mock_project_reports should be a fixture providing 'Project1' in DB
    project_names = ["Project1"]
    title = "My New Portfolio"

    # We patch get_engine to use our temp_db engine
    with patch("src.services.portfolio_service.get_engine", return_value=blank_db):
        model = generate_and_save_portfolio(project_names, title)

        assert model.id is not None

        # Load back via domain layer to verify content
        with Session(blank_db) as session:
            portfolio = load_portfolio(session, model.id)
            assert portfolio

            assert portfolio.metadata.project_ids_include == project_names
            # Check if generation logic (UserReport) created sections
            assert len(portfolio.sections) > 0


def test_update_portfolio_triggers_conflict(blank_db, mock_portfolio):
    """
    Verify that update_portfolio detects differences between
    existing user-edited content and new system generation.
    """
    with patch("src.services.portfolio_service.get_engine", return_value=blank_db):
        with Session(blank_db) as session:
            # 1. Setup: Save a portfolio that has a user edit
            # Note: mock_portfolio fixture should have a user edit timestamp
            saved_model = save_portfolio(session, mock_portfolio)
            session.commit()
            pid = saved_model.id

            assert pid

            # Simulate the user having edited a specific block
            # (Last user edit > Last generated)
            block = get_portfolio_block(session, pid, "intro_1", "tag_1")
            assert block
            block.user_updates(text="User custom intro")

            # Save the "Edited" state back to DB
            from src.database.api.CRUD.portfolio import update_portfolio_block
            update_portfolio_block(
                session, pid, "intro_1", "tag_1", text="User custom intro")
            session.commit()

        # 2. Act: Trigger update (System regeneration)
        # Assuming _create_portfolio would generate "Welcome to my portfolio!" for tag_1
        updated_model = update_portfolio(pid)

        # 3. Assert: The block should now be in conflict
        with Session(blank_db) as session:
            updated_domain = load_portfolio(session, pid)

            assert updated_domain

            target_block = updated_domain.sections[0].blocks_by_tag["tag_1"]

            assert target_block.is_in_conflict() is True
            assert target_block.current_content
            assert target_block.metadata.conflict_content
            assert target_block.current_content.text == "User custom intro"
            assert target_block.metadata.conflict_content.text == "Welcome to my portfolio!"


def test_merge_portfolios_adds_new_sections(mock_portfolio):
    """
    Test the pure domain logic of merge_portfolios:
    If generated has a section existing doesn't, it should be added.
    """
    from src.core.portfolio.sections.portfolio_section import PortfolioSection
    from src.core.portfolio.sections.block.block import Block

    existing = mock_portfolio  # Has 2 sections

    new_section = PortfolioSection("new_sec", "New Knowledge")
    new_section.add_block(Block("new_tag", TextBlock("New Content")))

    generated = Portfolio(sections=[new_section])

    # Act
    merged = merge_portfolios(existing, generated)

    # Assert
    # Existing sections remain, new one is added
    section_ids = [s.id for s in merged.sections]
    assert "intro_1" in section_ids
    assert "new_sec" in section_ids


def test_update_portfolio_nonexistent_raises(blank_db):
    """Verify KeyNotFoundError is raised for invalid IDs."""
    with patch("src.services.portfolio_service.get_engine", return_value=blank_db):
        from src.utils.errors import KeyNotFoundError
        with pytest.raises(KeyNotFoundError):
            update_portfolio(portfolio_id=99999)
