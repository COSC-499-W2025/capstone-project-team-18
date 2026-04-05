from sqlmodel import Session, select
import pytest
from src.core.portfolio.portfolio import Portfolio, PortfolioMetadata
from src.core.portfolio.sections.portfolio_section import PortfolioSection
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextBlock, TextListBlock
from src.database.api.models import BlockModel
from src.database.api.CRUD.portfolio import save_portfolio, load_portfolio, update_portfolio_block, get_portfolio_block


@pytest.fixture()
def mock_portfolio() -> Portfolio:
    """Fixture to create a nested portfolio structure for testing."""
    section_one = PortfolioSection("intro_1", "Intro Section")
    section_one.add_block(Block("tag_1", TextBlock("Hello World")))

    section_two = PortfolioSection("skills_1", "Skills Section")
    section_two.add_block(Block("tag_2", TextListBlock(["Python", "SQL"])))

    return Portfolio(
        sections=[section_one, section_two],
        metadata=PortfolioMetadata(project_ids=["A", "B"])
    )


def test_save_portfolio_persists_to_db(temp_db, mock_portfolio):
    """Verify that save_portfolio assigns an ID and puts the record in the DB."""
    with Session(temp_db) as session:
        # Save
        portfolio_model = save_portfolio(session, mock_portfolio)
        session.commit()

        # Verify ID was generated
        assert portfolio_model.id is not None

        # Verify it exists in the DB
        loaded = load_portfolio(session, portfolio_model.id)
        assert loaded is not None
        assert loaded.metadata.project_ids_include == ["A", "B"]


def test_load_portfolio_reconstructs_hierarchy(temp_db, mock_portfolio):
    """Verify that the 3-tier structure (Portfolio -> Section -> Block) is fully restored."""
    with Session(temp_db) as session:
        portfolio_model = save_portfolio(session, mock_portfolio)
        session.commit()
        pid = portfolio_model.id

        assert pid

        session.expunge_all()

        loaded_portfolio = load_portfolio(session, pid)

        assert loaded_portfolio is not None
        assert len(loaded_portfolio.sections) == 2

        intro_sec = loaded_portfolio.sections[0]
        assert intro_sec.title == "Intro Section"
        assert "tag_1" in intro_sec.blocks_by_tag

        block = intro_sec.blocks_by_tag["tag_1"]
        assert block.current_content is not None
        assert isinstance(block.current_content, TextBlock)
        assert block.current_content.text == "Hello World"



def test_load_nonexistent_portfolio_returns_none(temp_db):
    """Ensure we handle missing IDs gracefully."""
    with Session(temp_db) as session:
        result = load_portfolio(session, 99999)
        assert result is None


def test_crud_update_block_content(temp_db, mock_portfolio):
    """Verify that updating a block via CRUD persists and handles conflicts."""
    with Session(temp_db) as session:
        # Initial save of our fixture
        portfolio_model = save_portfolio(session, mock_portfolio)
        session.commit()
        pid = portfolio_model.id

        assert pid

        # Update the 'Intro Section' -> 'tag_1' (TextBlock)
        new_text = "Persisted Goodbye World"
        update_portfolio_block(
            session,
            portfolio_id=pid,
            section_tag="intro_1",
            block_tag="tag_1",
            text=new_text
        )
        session.commit()

        # Reload and verify
        loaded = load_portfolio(session, pid)
        assert loaded
        block = loaded.sections[0].blocks_by_tag["tag_1"]
        assert block.current_content.text == new_text  # type: ignore
        assert block.metadata.last_user_edit_at is not None


def test_crud_update_persists_content(temp_db, mock_portfolio):
    """Verify that a user update via CRUD persists the new content to the DB."""
    with Session(temp_db) as session:
        portfolio_model = save_portfolio(session, mock_portfolio)
        session.commit()
        pid = portfolio_model.id

        assert pid is not None

        update_portfolio_block(
            session,
            portfolio_id=pid,
            section_tag="skills_1",
            block_tag="tag_2",
            items=["Clean", "State"]
        )
        session.commit()

        block = get_portfolio_block(session, pid, "skills_1", "tag_2")

        assert block is not None
        assert block.current_content is not None
        assert block.current_content.raw_value() == ["Clean", "State"]  # type: ignore

        stmt = select(BlockModel).where(BlockModel.tag == "tag_2")
        db_block = session.exec(stmt).first()
        assert db_block.current_content == ["Clean", "State"]  # type: ignore
