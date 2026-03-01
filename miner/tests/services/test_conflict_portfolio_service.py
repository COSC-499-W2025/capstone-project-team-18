import pytest
from sqlmodel import Session
from src.utils.errors import KeyNotFoundError

from src.services.portfolio.edit_portfolio_service import get_portfolio_conflicts, resolve_block_accept_system
from src.core.portfolio.sections.block.block import Block
from src.database.api.CRUD.portfolio import save_portfolio
from src.core.portfolio.sections.block.block_content import TextBlock
from src.core.portfolio.portfolio import Portfolio, PortfolioSection


def setup_conflict_portfolio(session: Session) -> int:
    """Helper function to seed the database with a known conflict state using domain objects."""

    # 1. Create the base Domain Portfolio
    portfolio = Portfolio(title="Conflict Test Portfolio")

    # 2. Create a Domain Section
    section = PortfolioSection(
        section_id="summary_section", title="Summary Section")

    # 3. Create a Block and force it into a conflict state naturally
    block_conflict = Block[TextBlock]("summary_text")
    block_conflict.system_upload(TextBlock("Original system summary."))
    block_conflict.user_updates(text="My user generated summary.")

    # The second system upload triggers the conflict because the user has modified it
    block_conflict.system_upload(
        TextBlock("System generated updated summary."))

    # 4. Create a clean Block (no conflict)
    block_clean = Block[TextBlock]("contact_info")
    block_clean.system_upload(TextBlock("user@email.com"))

    # 5. Assemble the domain objects
    section.add_block(block_conflict)
    section.add_block(block_clean)
    portfolio.sections.append(section)

    # 6. Save the fully assembled domain portfolio to the database
    portfolio_model = save_portfolio(session, portfolio)
    session.commit()

    assert portfolio_model.id is not None

    return portfolio_model.id


def test_get_portfolio_conflicts(prs_db):
    """Tests that we can retrieve a formatted list of all blocks currently in conflict."""
    with Session(prs_db) as session:
        portfolio_id = setup_conflict_portfolio(session)

        conflicts = get_portfolio_conflicts(session, portfolio_id)

        assert len(
            conflicts) == 1, "Should only return the single block that is in conflict"

        conflict_data = conflicts[0]
        assert conflict_data["section_tag"] == "summary_section"
        assert conflict_data["block_tag"] == "summary_text"
        assert conflict_data["current_content"] == "My user generated summary."
        assert conflict_data["conflicting_content"] == "System generated updated summary."


def test_resolve_block_accept_system_success(prs_db):
    """Tests that resolving a conflict by accepting the system content works correctly."""
    with Session(prs_db) as session:
        portfolio_id = setup_conflict_portfolio(session)

        # Execute the resolution
        resolved_block = resolve_block_accept_system(
            session=session,
            portfolio_id=portfolio_id,
            section_tag="summary_section",
            block_tag="summary_text"
        )

        # Verify the state was correctly updated
        assert resolved_block.in_conflict is False
        assert resolved_block.conflict_content is None

        # The current content should now match what was previously in the conflict_content
        assert resolved_block.current_content == "System generated updated summary."


def test_resolve_block_accept_system_not_found(prs_db):
    """Tests that a KeyNotFoundError is raised if targeting a non-existent block."""
    with Session(prs_db) as session:
        portfolio_id = setup_conflict_portfolio(session)

        with pytest.raises(KeyNotFoundError, match="No block could be found"):
            resolve_block_accept_system(
                session=session,
                portfolio_id=portfolio_id,
                section_tag="summary_section",
                block_tag="ghost_block"  # This block does not exist
            )


def test_resolve_block_accept_system_invalid_state(prs_db):
    """Tests that a ValueError is raised if the block exists but is not in conflict."""
    with Session(prs_db) as session:
        portfolio_id = setup_conflict_portfolio(session)

        # Attempt to resolve 'contact_info', which has in_conflict=False
        with pytest.raises(ValueError, match="Invalid state, not in error"):
            resolve_block_accept_system(
                session=session,
                portfolio_id=portfolio_id,
                section_tag="summary_section",
                block_tag="contact_info"
            )
