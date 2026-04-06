from dataclasses import dataclass
from typing import Optional, TypeVar, Generic
from datetime import datetime
from .block_content import BlockContent
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BlockContent)


@dataclass
class BlockMetadata(Generic[T]):
    """Metadata about the content, including timestamps for last generation and user edit."""
    last_generated_at: Optional[datetime] = None
    last_user_edit_at: Optional[datetime] = None


class Block(Generic[T]):
    """
    A block in the portfolio. Contains content along with metadata.
    System regeneration always overwrites user changes.
    """

    tag: str  # A unique key to identify the block in the PortfolioSection
    generated_by: str  # Section title
    current_content: T | None
    metadata: BlockMetadata

    def __init__(self, tag: str, initial_content: T | None = None, system_created: bool = True):
        self.tag = tag
        self.current_content: T | None = None
        self.metadata = BlockMetadata[T]()

        if initial_content:
            self.update_current_content(
                initial_content, system_created=system_created)

    def update_current_content(self, new_content: T, system_created: bool):
        """
        Set the block content. Writes directly — no conflict tracking.
        """

        self.current_content = new_content

        if system_created:
            self.metadata.last_generated_at = datetime.now()
            logger.info("System content updated.")
        else:
            self.metadata.last_user_edit_at = datetime.now()
            logger.info("User content updated.")

    def user_updates(self, **kwargs):
        """
        Update the current content based on kwargs.
        Implementation details are handled by the respective BlockContent.
        """
        if self.current_content is None:
            raise ValueError("Cannot update a block with no current_content")

        self.current_content.update(**kwargs)
        logger.info(f"User updated block content with {kwargs}")
        self.update_current_content(self.current_content, system_created=False)

    def system_upload(self, content: T):
        """
        Called by the portfolio generation system. Always overwrites current content.
        """
        self.update_current_content(content, system_created=True)
