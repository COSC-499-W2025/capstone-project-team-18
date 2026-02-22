import pytest

from src.core.portfolio.sections.portfolio_section import (
    PortfolioSection,
    merge_section,
)
from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextBlock


def make_text_block(tag: str, text: str) -> Block[TextBlock]:
    block = Block[TextBlock](tag)
    block.system_upload(TextBlock(text))
    return block


def test_section_initial_state():
    section = PortfolioSection("s1", "Experience")

    assert section.id == "s1"
    assert section.title == "Experience"
    assert section.blocks_by_tag == {}
    assert section.block_order == []


def test_add_block_preserves_order():
    section = PortfolioSection("s1", "Experience")

    b1 = make_text_block("a", "A")
    b2 = make_text_block("b", "B")

    section.add_block(b1)
    section.add_block(b2)

    assert section.block_order == ["a", "b"]
    assert section.blocks_by_tag["a"] is b1
    assert section.blocks_by_tag["b"] is b2


def test_add_block_duplicate_tag_raises():
    section = PortfolioSection("s1", "Experience")

    b1 = make_text_block("a", "A")
    b2 = make_text_block("a", "B")

    section.add_block(b1)

    with pytest.raises(ValueError):
        section.add_block(b2)


def test_remove_block_preserves_other_order():
    section = PortfolioSection("s1", "Experience")

    a = make_text_block("a", "A")
    b = make_text_block("b", "B")
    c = make_text_block("c", "C")

    section.add_block(a)
    section.add_block(b)
    section.add_block(c)

    section.remove_block("b")

    assert section.block_order == ["a", "c"]
    assert "b" not in section.blocks_by_tag


def test_remove_nonexistent_block_is_noop():
    section = PortfolioSection("s1", "Experience")

    section.remove_block("missing")  # should not raise


def test_edit_block_updates_content():
    section = PortfolioSection("s1", "Experience")

    block = make_text_block("summary", "Hello")
    section.add_block(block)

    section.edit_block("summary", text="Updated")

    assert block.current_content is not None
    assert block.current_content.text == "Updated"


def test_edit_missing_block_is_noop():
    section = PortfolioSection("s1", "Experience")

    section.edit_block("missing", text="hello")  # should not raise


def test_render_renders_blocks_in_order():
    section = PortfolioSection("s1", "Experience")

    a = make_text_block("a", "A")
    b = make_text_block("b", "B")

    section.add_block(a)
    section.add_block(b)

    assert section.render() == "A\n\nB"


def test_render_empty_section():
    section = PortfolioSection("s1", "Experience")

    assert section.render() == ""


def test_tags_of_blocks_in_conflict():
    section = PortfolioSection("s1", "Experience")

    a = make_text_block("a", "A")
    b = make_text_block("b", "B")

    section.add_block(a)
    section.add_block(b)

    # force conflict
    b.metadata.in_conflict = True

    assert section.tags_of_blocks_in_conflict() == ["b"]


def test_conflict_tags_respect_section_order():
    section = PortfolioSection("s1", "Experience")

    a = make_text_block("a", "A")
    b = make_text_block("b", "B")
    c = make_text_block("c", "C")

    section.add_block(a)
    section.add_block(b)
    section.add_block(c)

    c.metadata.in_conflict = True
    a.metadata.in_conflict = True

    assert section.tags_of_blocks_in_conflict() == ["a", "c"]


def test_merge_updates_existing_block():
    existing = PortfolioSection("s1", "Experience")
    generated = PortfolioSection("s1", "Experience")

    existing_block = make_text_block("summary", "Old")
    generated_block = make_text_block("summary", "New")

    existing.add_block(existing_block)
    generated.add_block(generated_block)

    merge_section(existing, generated)

    assert existing_block.current_content is not None
    assert existing_block.current_content.text == "New"


def test_merge_adds_new_block():
    existing = PortfolioSection("s1", "Experience")
    generated = PortfolioSection("s1", "Experience")

    new_block = make_text_block("summary", "Hello")
    generated.add_block(new_block)

    merge_section(existing, generated)

    assert "summary" in existing.blocks_by_tag
    assert existing.block_order == ["summary"]


def test_merge_preserves_existing_block_order():
    existing = PortfolioSection("s1", "Experience")
    generated = PortfolioSection("s1", "Experience")

    a = make_text_block("a", "A")
    b = make_text_block("b", "B")
    c = make_text_block("c", "C")

    existing.add_block(a)
    existing.add_block(b)
    generated.add_block(c)

    merge_section(existing, generated)

    assert existing.block_order == ["a", "b", "c"]
