from datetime import datetime, timedelta
import pytest

from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextBlock


def test_block_initial_state():
    block = Block[TextBlock]("test_key")

    assert block.metadata.in_conflict is False
    assert block.metadata.conflict_content is None
    assert block.metadata.last_generated_at is None
    assert block.metadata.last_user_edit_at is None


def test_system_upload_overwrites_previous_system_content():
    block = Block[TextBlock]("test_key")

    block.system_upload(TextBlock("A"))
    block.system_upload(TextBlock("B"))

    assert block.current_content is not None
    assert block.current_content.text == "B"
    assert block.is_in_conflict() is False


def test_system_creates_text_block():
    """
    Test with a TextBlock, we can get give the current content
    """

    content = "Hello, World!"

    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock(content))

    assert block.current_content is not None
    assert block.current_content.text == content
    assert block.is_in_conflict() is False


def test_text_block_update():
    """
    Test with a TextBlock: system can create the
    text block, then a user can update that block.
    """

    content = "Hello, World!"
    update_content = "goodbye, world!"

    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock(content))
    block.user_updates(text=update_content)

    assert block.current_content is not None
    assert block.current_content.text == update_content
    assert block.metadata.last_user_edit_at is not None
    assert datetime.now() - block.metadata.last_user_edit_at < timedelta(seconds=3)
    assert block.is_in_conflict() is False


def test_user_update_without_system_content_raises():
    block = Block[TextBlock]("test_key")

    with pytest.raises(ValueError):
        block.user_updates(text="hello")
