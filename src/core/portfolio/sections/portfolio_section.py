
from src.infrastructure.log.logging import get_logger
from .block.block import Block

logger = get_logger(__name__)


class PortfolioSection:
    """
    A section in the portfolio. Maintains an ordered list of blocks,
    each with a unique section-level tag. Blocks can be added, removed,
    or updated, with full conflict handling.
    """

    id: str
    title: str
    blocks: list[Block]
    blocks_by_tag: dict[str, Block]
    order: int = 0

    def __init__(self, section_id: str, title: str):
        self.id = section_id
        self.title = title
        self.blocks_by_tag: dict[str, Block] = {}
        self.block_order: list[str] = []

    def add_block(self, block: Block):
        """
        Add a new block to the section. The block must have a unique tag.
        """
        if block.tag in self.blocks_by_tag:
            raise ValueError(
                f"Block tag '{block.tag}' already exists in section '{self.title}'")

        self.blocks_by_tag[block.tag] = block
        self.block_order.append(block.tag)

        logger.info(f"Added block '{block.tag}' to section '{self.title}'")

    def remove_block(self, tag: str):
        """
        Remove a block by its tag.
        """
        if tag in self.blocks_by_tag:
            del self.blocks_by_tag[tag]
            self.block_order.remove(tag)
            logger.info(f"Removed block '{tag}' from section '{self.title}'")
        else:
            logger.warning(
                f"Tried to remove non-existent block '{tag}' from section '{self.title}'")

    def edit_block(self, tag: str, **kwargs):
        """
        Edit the content of a block via its tag. Pass kwargs to the Block's user_updates().
        """

        block = self.blocks_by_tag.get(tag)

        if block is None:
            logger.warning(
                f"Tried to edit non-existent block '{tag}' in section '{self.title}'")
            return
        block.user_updates(**kwargs)
        logger.info(
            f"Edited block '{tag}' in section '{self.title}' with {kwargs}")

    def render(self) -> str:
        """Render all content items in this section."""

        if not self.blocks:
            return ""
        return "\n\n".join(block.current_content.render() for block in self.blocks)

    def add_content(self, block: Block):
        """Add a new block to the section."""
        self.blocks.append(block)
        logger.info(
            f"Added new block to section '{self.title}' (id={self.id})")

    def remove_content(self, index: int):
        """Remove a block by index."""
        if 0 <= index < len(self.blocks):
            removed = self.blocks.pop(index)
            logger.info(
                f"Removed block at index {index} from section '{self.title}' (id={self.id})")
        else:
            logger.warning(
                f"Tried to remove invalid index {index} from section '{self.title}'")

    def edit_content(self, index: int, **kwargs):
        """
        Edit the content of a block at a given index.
        kwargs are passed to Block.user_updates().
        """
        if 0 <= index < len(self.blocks):
            block = self.blocks[index]
            block.user_updates(**kwargs)
            logger.info(
                f"Edited block at index {index} in section '{self.title}' (id={self.id}) with {kwargs}")
        else:
            logger.warning(
                f"Tried to edit invalid index {index} in section '{self.title}'")

    def indexs_of_blocks_in_conflict(self) -> list[int]:
        """
        Return a list of indices for all blocks in this section that are currently in conflict.
        """
        return [i for i, block in enumerate(self.blocks) if block.metadata.in_conflict]


def merge_section(existing: PortfolioSection, generated: PortfolioSection):
    """
    Merge a newly generated section into an existing section.
    Conflicts are recorded in the respective blocks.
    """

    # Step 1: Index existing blocks by tag
    existing_blocks = existing.blocks_by_tag

    for new_block_tag, new_block in generated.blocks_by_tag.items():
        if new_block_tag in existing_blocks:
            existing_block = existing_blocks[new_block_tag]

            existing_block.system_upload(new_block.current_content)

        else:
            # Step 3: If this is a brand new block, just add it
            existing.add_block(new_block)
            logger.info(
                f"New block '{new_block_tag}' added to section '{existing.title}'")
