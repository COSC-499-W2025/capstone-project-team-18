"""
This file defines both a serializer and a deserializer method for
any statistic value.
"""

from enum import Enum
from dataclasses import is_dataclass, asdict
from typing import Any
import ast
import json
from datetime import datetime
from src.core.statistic.statistic_models import FileDomain, CodingLanguage, WeightedSkills
from src.infrastructure.log.logging import get_logger
from src.utils.errors import UnhandledValue, UnkownDeserializationClass

logger = get_logger(__name__)

ENUM_REGISTRY = {
    "FileDomain": FileDomain,
    "CodingLanguage": CodingLanguage,
}

DATACLASS_REGISTRY = {
    "WeightedSkills": WeightedSkills,
}


def serialize(value: Any) -> Any:
    """
    Converts a value from a statistic into JSON-compatible data

    :param value: Any enum, dataclass, datetime, etc value from a Statistic
    :type value: Any
    :return: List, str, or object. It will be JSON-compatible.
    :rtype: Any
    """
    if value is None:
        return None

    if isinstance(value, Enum):
        # If it's an Enum, store its class name and value
        return {"__type__": "enum", "class": value.__class__.__name__, "value": value.value}

    if is_dataclass(value) and not isinstance(value, type):
        # If it is a Dataclass instance, store its class name and asdict representation
        return {"__type__": "dataclass", "class": value.__class__.__name__, "value": asdict(value)}

    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}

    if isinstance(value, dict):
        # If it's a dict, serialize keys and values
        new_dict = {}
        for k, v in value.items():
            new_key = _serialize_dict_key(k)
            new_dict[new_key] = serialize(v)
        return new_dict

    if isinstance(value, list):
        # If it's a list, serialize each element
        return [serialize(v) for v in value]

    return value


def deserialize(value: Any):
    """
    Intakes a JSON value that was converted with the serialize function and
    returns the proper, orginal enum, dataclass, datetime, etc.

    :param value: The value for a JSON key
    :type value: Any
    :return: The proper expected type for the statistic
    :rtype: Any
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
            if value["__type__"] == "datetime":
                return datetime.fromisoformat(value["value"])

        # Otherwise, it's a regular dict; deserialize keys and values recursively
        # and reconstruct the original dict.
        new_dict = {}
        for k, v in value.items():
            orig_key = _deserialize_dict_key(k)
            new_dict[orig_key] = deserialize(v)
        return new_dict

    if isinstance(value, list):
        return [deserialize(v) for v in value]

    return value


def _serialize_dict_key(key: Any) -> str:
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


def _deserialize_dict_key(key: str) -> Any:
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
            logger.debug(
                f"Tried to parse value: {val} for a type. It failed. Expected if this value is a string.")
            pass
        except SyntaxError:
            raise UnhandledValue(
                f"Tried to parse value: {val} failed by syntax")

        cls = ENUM_REGISTRY.get(cls_name, None)

        if cls is None:
            raise UnkownDeserializationClass(
                f"Tried to find {cls} in the enum registry but failed")

        return cls(val)

    if key.startswith("__dataclass__:"):
        _, cls_name, val_str = key.split(":", 2)
        val_dict = json.loads(val_str)

        cls = DATACLASS_REGISTRY.get(cls_name, None)

        if cls is None:
            raise UnkownDeserializationClass(
                f"Tried to find {cls} in the dataclass registry but failed")

        return cls(**val_dict)

    return key
