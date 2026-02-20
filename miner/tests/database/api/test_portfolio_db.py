from sqlmodel import Session
import pytest
from src.core.portfolio.portfolio import Portfolio, PortfolioMetadata
from src.core.portfolio.sections.portfolio_section import PortfolioSection
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextBlock, TextListBlock
from src.database.api.CRUD.portfolio import save_portfolio, load_portfolio


@pytest.fixture()
def mock_portfolio() -> Portfolio:
    """Fixture to create a nested portfolio structure for testing."""
    section_one = PortfolioSection("intro_1", "Intro Section")
    section_one.add_block(Block("tag_1", TextBlock("Hello World")))

    section_two = PortfolioSection("skills_1", "Skills Section")
    skills_block = Block("tag_2", TextListBlock(["Python", "SQL"]))

    # Simulate a conflict state
    skills_block.metadata.in_conflict = True
    skills_block.metadata.conflict_content = TextListBlock(
        ["Python", "SQL", "Java"]
    )

    section_two.add_block(skills_block)

    return Portfolio(
        sections=[section_one, section_two],
        metadata=PortfolioMetadata(project_ids=[101, 102])
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
        assert loaded.metadata.project_ids_include == [101, 102]


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


def test_load_portfolio_preserves_conflicts(temp_db, mock_portfolio):
    """Verify that the conflict metadata and content survive the DB trip."""
    with Session(temp_db) as session:
        saved = save_portfolio(session, mock_portfolio)
        session.commit()
        pid = saved.id

        assert pid

        loaded = load_portfolio(session, pid)
        assert loaded

        skills_block = loaded.sections[1].blocks_by_tag["tag_2"]

        assert skills_block.metadata.in_conflict is True
        assert isinstance(
            skills_block.metadata.conflict_content, TextListBlock)
        assert "Java" in skills_block.metadata.conflict_content.items


def test_load_nonexistent_portfolio_returns_none(temp_db):
    """Ensure we handle missing IDs gracefully."""
    with Session(temp_db) as session:
        result = load_portfolio(session, 99999)
        assert result is None
