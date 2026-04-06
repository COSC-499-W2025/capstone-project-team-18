
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
    block_order: list[str]
    blocks_by_tag: dict[str, Block]
    order: int = 0

    def __init__(self, section_id: str, title: str):
        self.id = section_id
        self.title = title
        self.blocks_by_tag: dict[str, Block] = {}
        self.block_order: list[str] = []

    def add_block(self, block: Block):
        """
        Adds a block to the section. For add_block, the order is perserved, meaning
        that the first add_block() with add to the top of the section, and a second
        call add_block() will be under it.
        """

        if block.tag in self.blocks_by_tag:
            raise ValueError(
                f"Block tag '{block.tag}' already exists in section '{self.title}'")

        self.blocks_by_tag[block.tag] = block
        self.block_order.append(block.tag)

        logger.info(f"Added block '{block.tag}' to section '{self.title}'")

    def remove_block(self, tag: str):
        """
        Remove a block in the section by tag. Order of other blocks are perserved.
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
        Edit the content of a block via its tag. Passes kwargs to the Block's user_updates().
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

        return "\n\n".join(
            self.blocks_by_tag[tag].current_content.render()  # type: ignore
            for tag in self.block_order
            if self.blocks_by_tag[tag].current_content is not None
        )

def merge_section(existing: PortfolioSection, generated: PortfolioSection) -> PortfolioSection:
    """
    Merge a newly generated section into an existing section.
    System-generated content always overwrites existing content.
    """

    existing_blocks = existing.blocks_by_tag

    for new_block_tag, new_block in generated.blocks_by_tag.items():
        if new_block_tag in existing_blocks:
            existing_blocks[new_block_tag].system_upload(new_block.current_content)
        else:
            existing.add_block(new_block)
            logger.info(
                f"New block '{new_block_tag}' added to section '{existing.title}'")

    return existing
