from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar, Generic, List


T = TypeVar("T", bound="BlockContent")
RawValue = TypeVar("RawValue")


class BlockContentType(str, Enum):
    """
    A enum tracking all the types of content that
    could be shown in a block.
    """

    TEXT = "Text"
    TEXT_LIST = "TextList"


class BlockContent(ABC, Generic[RawValue]):
    """
    The base class for content to be displayed in the portfolio.
    """
    content_type: BlockContentType

    @abstractmethod
    def render(self) -> str:
        """Return a human-readable representation of the content."""
        pass

    @abstractmethod
    def update(self, **kwargs):
        """
        Update content fields. Each subclass handles its own keys.
        """
        pass

    @abstractmethod
    def raw_value(self) -> RawValue:
        """
        Return the "raw" Python type representing the content. Must
        also be JSON serializable!
        """
        pass


@dataclass
class TextBlock(BlockContent[str]):
    text: str
    content_type: BlockContentType = BlockContentType.TEXT

    def render(self) -> str:
        return self.text

    def update(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]
            return

    def raw_value(self) -> str:
        return self.text

    @classmethod
    def expected_update_fields(cls) -> dict[str, Any]:
        return {
            "type": "Text",
            "update": {
                "text": "new text to store",
            }
        }


@dataclass
class TextListBlock(BlockContent[List[str]]):

    items: list[str]
    content_type: BlockContentType = BlockContentType.TEXT_LIST

    def render(self) -> str:
        return "\n".join(f"- {i}" for i in self.items)

    def update(self, **kwargs):
        if "items" in kwargs:  # replace entire list
            self.items = kwargs["items"]
        if "add" in kwargs:  # add a single item
            self.items.append(kwargs["add"])
        if "edit" in kwargs:  # expects tuple (index, new_value)
            index, value = kwargs["edit"]
            if 0 <= index < len(self.items):
                self.items[index] = value
        if "remove" in kwargs:  # remove a single item
            self.items = [i for i in self.items if i != kwargs["remove"]]

    def raw_value(self) -> List[str]:
        return self.items

    @classmethod
    def expected_update_fields(cls) -> dict[str, Any]:
        return {
            "type": "TextList",
            "update": {
                "items": "list[str] (replace entire list)",
                "add": "str (add a single item)",
                "edit": "tuple[int, str] (edit item at index)",
                "remove": "str (remove an item)"
            }
        }
