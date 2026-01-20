"""
This file defines a custom SQLAlchemy column type that serializes and deserializes
various complex Python objects (enums, dataclasses, dates, dicts, lists) for storage in a JSON column.
"""

from sqlalchemy.types import TypeDecorator, JSON
from enum import Enum
from dataclasses import is_dataclass, asdict
from typing import Any
import ast
import json
from src.core.statistic import FileDomain, CodingLanguage, WeightedSkills

ENUM_REGISTRY = {
    "FileDomain": FileDomain,
    "CodingLanguage": CodingLanguage,
}

DATACLASS_REGISTRY = {
    "WeightedSkills": WeightedSkills,
}


class ColumnStatisticSerializer(TypeDecorator):
    """
    This is a custom SQLAlchemy column type that serializes and deserializes
    our complex Statistic value objects. If we are here, we know we need to serialize
    or deserialize the value to/from a JSON-compatible format. Other primitive
    types (str, int, float, bool, None) are handled elsewhere.

    For special enums and dataclasses, we store their class name metadata along with their value
    so we can reconstruct them later during deserialization.

    """

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return self._serialize(value)

    def process_result_value(self, value, dialect):
        return self._deserialize(value)

    def _serialize(self, value: Any):
        """
        Serialize the value into a JSON-compatible format.
        """

        if value is None:
            return None

        if isinstance(value, Enum):
            # If it's an Enum, store its class name and value
            return {"__type__": "enum", "class": value.__class__.__name__, "value": value.value}

        if is_dataclass(value) and not isinstance(value, type):
            # If it is a Dataclass instance, store its class name and asdict representation
            return {"__type__": "dataclass", "class": value.__class__.__name__, "value": asdict(value)}

        if isinstance(value, dict):
            # If it's a dict, serialize keys and values
            new_dict = {}
            for k, v in value.items():
                new_key = self._serialize_dict_key(k)
                new_dict[new_key] = self._serialize(v)
            return new_dict

        if isinstance(value, list):
            # If it's a list, serialize each element
            return [self._serialize(v) for v in value]

        return value

    def _deserialize(self, value: Any):
        """
        Deserialize the value from its JSON-compatible format back into the original type.
        """

        if value is None:
            return None

        # Dict
        if isinstance(value, dict):

            if "__type__" in value:
                # We have a special serialized type and thus we need to deserialize it
                # explicitly by looking up its class in the registry and reconstructing it.
                if value["__type__"] == "enum":
                    cls = ENUM_REGISTRY[value["class"]]
                    return cls(value["value"])
                if value["__type__"] == "dataclass":
                    cls = DATACLASS_REGISTRY[value["class"]]
                    return cls(**value["value"])

            # Otherwise, it's a regular dict; deserialize keys and values recursively
            # and reconstruct the original dict.
            new_dict = {}
            for k, v in value.items():
                orig_key = self._deserialize_dict_key(k)
                new_dict[orig_key] = self._deserialize(v)
            return new_dict

        if isinstance(value, list):
            return [self._deserialize(v) for v in value]

        return value

    def _serialize_dict_key(self, key: Any) -> str:
        """
        JSON format requires dict keys to be strings. So, if we have a complex key
        (like an Enum or Dataclass), we need to serialize it into a string. We do this
        by converting it into a special string format that we can later parse back.
        """

        if isinstance(key, Enum):
            return f"__enum__:{key.__class__.__name__}:{key.value}"
        if is_dataclass(key) and not isinstance(key, type):
            return f"__dataclass__:{key.__class__.__name__}:{json.dumps(asdict(key))}"
        return str(key)

    def _deserialize_dict_key(self, key: str) -> Any:
        """
        Deserialize a dict key from its string representation back into the original type. We do this
        by checking for our special string formats and reconstructing the original object by looking
        up its class in the registry, then instantiating it with the stored value.
        """

        if key.startswith("__enum__:"):
            _, cls_name, val_str = key.split(":", 2)

            val = val_str

            try:
                val = ast.literal_eval(val_str)
            except ValueError:
                # If we are here, then ast tried to evaluate a string
                # which lead to a malformed string error. In this case
                # we treat the value to just be the val_str. The cls(val)
                # statement will error out if this was not the right choice
                pass

            cls = ENUM_REGISTRY[cls_name]
            return cls(val)

        if key.startswith("__dataclass__:"):
            _, cls_name, val_str = key.split(":", 2)
            val_dict = json.loads(val_str)
            cls = DATACLASS_REGISTRY[cls_name]
            return cls(**val_dict)
        return key
