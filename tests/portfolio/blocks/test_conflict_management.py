from datetime import datetime, timedelta
import pytest

from src.core.portfolio.sections.block.block import Block
from src.core.portfolio.sections.block.block_content import TextBlock
from src.core.portfolio.sections.block.block_content import TextListBlock


def test_conflict():
    """
    Test with a TextBlock: system can create the
    text block, then a user can update that block,
    then if the system tries to update again, they
    are in conflict mode
    """

    system_content = "Hello, World!"
    user_content = "goodbye, world!"
    system_conflicting_content = "See you, world!"

    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock(system_content))
    block.user_updates(text=user_content)
    block.system_upload(TextBlock(system_conflicting_content))

    assert block.current_content.text == user_content
    assert block.metadata.conflict_content is not None
    assert block.metadata.conflict_content.raw_value() == system_conflicting_content
    assert block.metadata.last_generated_at is not None
    assert block.metadata.last_user_edit_at is not None
    assert block.is_in_conflict() is True


def test_text_list_block_conflict():
    block = Block[TextListBlock]("test_key")

    block.system_upload(TextListBlock(["a", "b"]))
    block.user_updates(add="c")
    block.system_upload(TextListBlock(["x", "y"]))

    assert block.is_in_conflict() is True
    assert block.metadata.conflict_content is not None
    assert block.current_content.raw_value() == ["a", "b", "c"]
    assert block.metadata.conflict_content.raw_value() == ["x", "y"]


def test_system_regenerating_same_user_content_does_not_conflict():
    """
    Test with a TextBlock: system can create the
    text block, then a user can update that block,
    then if the system tries to update again, they
    are in conflict mode
    """

    system_content = "Hello, World!"
    user_content = "goodbye, world!"
    system_conflicting_content = user_content

    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock(system_content))
    block.user_updates(text=user_content)
    block.system_upload(TextBlock(system_conflicting_content))

    assert block.current_content.text == user_content
    assert block.is_in_conflict() is False

    assert block.metadata.last_generated_at is not None
    assert block.metadata.last_user_edit_at is not None
    assert block.metadata.last_generated_at > block.metadata.last_user_edit_at


def test_conflict_then_another_conflict():
    """
    Test what happens when a block gets into a conflict
    and then another conflict happens
    """

    system_content = "Hello, World!"
    user_content = "goodbye, world!"
    system_conflicting_content = "See you, world!"
    system_double_conflicting_content = "YAPYAP"

    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock(system_content))
    block.user_updates(text=user_content)
    block.system_upload(TextBlock(system_conflicting_content))
    block.system_upload(TextBlock(system_double_conflicting_content))

    assert block.current_content.text == user_content
    assert block.metadata.conflict_content is not None
    assert block.metadata.conflict_content.raw_value(
    ) == system_double_conflicting_content
    assert block.metadata.last_generated_at is not None
    assert block.metadata.last_user_edit_at is not None
    assert block.is_in_conflict() is True


def test_conflict_accept_system():
    """
    Test with a TextBlock: system can create the
    text block, then a user can update that block,
    then if the system tries to update again, they
    are in conflict mode.

    """

    system_content = "Hello, World!"
    user_content = "goodbye, world!"
    system_conflicting_content = "See you, world!"

    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock(system_content))
    block.user_updates(text=user_content)
    block.system_upload(TextBlock(system_conflicting_content))
    block.resolve_conflict_accept_system()

    assert block.current_content.text == system_conflicting_content
    assert block.metadata.last_generated_at is not None
    assert datetime.now() - block.metadata.last_generated_at < timedelta(seconds=1)
    assert block.metadata.conflict_content is None
    assert block.is_in_conflict() is False


def test_conflict_user_updates():
    """
    Test with a TextBlock: system can create the
    text block, then a user can update that block,
    then if the system tries to update again, they
    are in conflict mode.

    """

    system_content = "Hello, World!"
    user_content = "goodbye, world!"
    system_conflicting_content = "See you, world!"
    user_update = "YAPYAP"

    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock(system_content))
    block.user_updates(text=user_content)
    block.system_upload(TextBlock(system_conflicting_content))
    block.resolve_conflict_update_current(text=user_update)

    assert block.current_content.text == user_update
    assert block.metadata.last_user_edit_at is not None
    assert datetime.now() - block.metadata.last_user_edit_at < timedelta(seconds=1)
    assert block.metadata.conflict_content is None
    assert block.is_in_conflict() is False


def test_conflict_resolve_does_not_touch_timestamps():
    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock("A"))
    block.user_updates(text="B")
    block.system_upload(TextBlock("C"))

    last_gen = block.metadata.last_generated_at
    last_user = block.metadata.last_user_edit_at

    block.conflict_resolve()

    assert block.metadata.last_generated_at == last_gen
    assert block.metadata.last_user_edit_at == last_user


def test_accept_system_without_conflict_raises():
    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock("A"))

    with pytest.raises(ValueError):
        block.resolve_conflict_accept_system()


def test_accept_update_without_conflict_raises():
    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock("A"))

    with pytest.raises(ValueError):
        block.resolve_conflict_update_current()


def test_system_upload_during_conflict_does_not_mutate_current():
    block = Block[TextBlock]("test_key")
    block.system_upload(TextBlock("A"))
    block.user_updates(text="B")
    block.system_upload(TextBlock("C"))

    current = block.current_content.text
    block.system_upload(TextBlock("D"))

    assert block.current_content.text == current
    assert block.metadata.conflict_content is not None
    assert block.metadata.conflict_content.raw_value() == "D"
