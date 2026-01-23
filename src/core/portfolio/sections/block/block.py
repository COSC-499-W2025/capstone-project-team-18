from dataclasses import dataclass
from typing import Optional, TypeVar, Generic
from datetime import datetime
from .block_content import BlockContent
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BlockContent)


@dataclass
class BlockMetadata(Generic[T]):
    """
    Metadata about the content. Includes vars needed
    for version control and merge handling (i.e what
    happens when a user makes an edit and tries to
    regenerate)
    """
    last_generated_at: Optional[datetime] = None
    last_user_edit_at: Optional[datetime] = None

    # Version Control and Merge Handling
    in_conflict: bool = False
    conflict_content: Optional[T] = None


class Block(Generic[T]):
    """
    A block in the portfolio. Contains both a user-generated
    and a system-generated content, along with metadata.
    Provides logic for updating, merging, and conflict handling.
    """

    tag: str  # A unquie key to identify the block in the PortfolioSection
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

    def is_in_conflict(self):
        return self.metadata.in_conflict

    def update_current_content(self, new_content: T, system_created: bool):
        """
        Set what content this block contains to the new content. This is a destructive
        function as it does not check to see if there are merge conflicts, will
        resolve any pending conflicts and writes directly to the block.
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
        This function will update the current content in the block
        based on the kwargs passed in. The implementation details
        of each content type are handled by the respective BlockContent.
        """
        if self.metadata.in_conflict:
            logger.warning(
                "User updating content while in conflict; resolving conflict.")
            self.conflict_resolve()

        if self.current_content is None:
            raise ValueError("Cannot update a block with no current_content")

        self.current_content.update(**kwargs)
        logger.info(f"User updated block content with {kwargs}")
        self.update_current_content(self.current_content, system_created=False)

    def system_upload(self, content: T):
        """
        This function should only be called by the portfolio generation
        system.
        """

        # Would uploading this system data overwrite user changes?
        is_conflict = self.metadata.in_conflict or (
            self.metadata.last_user_edit_at is not None
            and self.metadata.last_generated_at is not None
            and self.metadata.last_user_edit_at > self.metadata.last_generated_at
            and (self.current_content is None or self.current_content.render() != content.render())
        )

        if not is_conflict:
            self.update_current_content(content, system_created=True)
        else:
            self.metadata.conflict_content = content
            self.metadata.in_conflict = True
            logger.warning(
                "Conflict detected between user and system content.")

    def resolve_conflict_accept_system(self):
        """
        Conflict is resolved by the user accepting the systems,
        conflict content
        """
        if not self.is_in_conflict():
            raise ValueError("Invalid state, not in error")

        if self.metadata.conflict_content is None:
            raise ValueError(
                "Invalid state! Trying to accept conflicting content, "
                "but Block does not know what content was conflicting"
            )

        self.update_current_content(self.metadata.conflict_content, True)
        self.conflict_resolve()

        logger.info("Conflict resolved: user accepted system content.")

    def resolve_conflict_update_current(self, **kwargs):
        """
        Resolve conflict by updating the current content.
        """

        if not self.is_in_conflict():
            raise ValueError("Invalid state, not in error")

        self.user_updates(**kwargs)
        self.conflict_resolve()

        logger.info(
            f"Conflict resolved by user updating content with {kwargs}")

    def conflict_resolve(self):
        """
        Sets metadata state back to no conflict
        """
        self.metadata.conflict_content = None
        self.metadata.in_conflict = False
        logger.info("Conflict state cleared.")
