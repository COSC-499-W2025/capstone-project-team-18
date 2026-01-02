"""
Tests for ColumnStatisticSerializer to ensure non-primitive types (enums, dataclasses,
nested structures, dict keys/values) serialize and deserialize correctly.
"""

from typing import Dict, Any
import pytest
import json

from datetime import date

from src.classes.statistic.statistic_models import WeightedSkills, CodingLanguage, FileDomain
from src.database.utils.column_statistic_serializer import ColumnStatisticSerializer


@pytest.fixture
def serializer() -> ColumnStatisticSerializer:
    return ColumnStatisticSerializer()


def test_dataclass_direct_serialize_deserialize(serializer: ColumnStatisticSerializer):
    ws = WeightedSkills("Python", 0.9)
    serialized = serializer._serialize(ws)

    assert isinstance(serialized, dict)
    assert serialized["__type__"] == "dataclass"
    assert serialized["class"] == "WeightedSkills"
    assert serialized["value"] == {"skill_name": "Python", "weight": 0.9}

    recovered = serializer._deserialize(serialized)
    assert isinstance(recovered, WeightedSkills)
    assert recovered == ws


@pytest.mark.parametrize(
    "value, expected_type",
    [
        # --- dates ---
        (date(2024, 1, 1), date),

        # --- enums ---
        (FileDomain.CODE, FileDomain),
        (CodingLanguage.PYTHON, CodingLanguage),

        # --- dataclass ---
        (WeightedSkills("Python", 0.9), WeightedSkills),

        # --- lists ---
        (["python", "testing"], list),
        ([WeightedSkills("Python", 0.9), WeightedSkills("SQL", 0.7)], list),

        # --- dicts ---
        ({"file1.py": 3, "file2.py": 2}, dict),
        ({FileDomain.CODE: 0.4, FileDomain.TEST: 0.6}, dict),
        ({CodingLanguage.PYTHON: 0.8, CodingLanguage.SQL: 0.2}, dict),
    ],
    ids=[
        "date",
        "file-domain-enum",
        "coding-language-enum",
        "weighted-skills",
        "list-of-str",
        "list-of-weighted-skills",
        "plain-dict",
        "dict-filedomain-float",
        "dict-codinglanguage-float",
    ],
)
def test_non_trivial_serialize_deserialize(
    serializer: ColumnStatisticSerializer,
    value,
    expected_type,
):
    """
    Try to serialize and then deserialize every non-trival
    expected_type in the statistics. We use the parameters
    described in the annonation to determine value and expected_type
    """
    serialized = serializer._serialize(value)

    json_serialize = json.dumps(serialized)
    json_loaded_to_dict = json.loads(json_serialize)

    recovered = serializer._deserialize(json_loaded_to_dict)

    assert isinstance(recovered, expected_type)
    assert recovered == value


def test_enum_direct_serialize_deserialize(serializer: ColumnStatisticSerializer):
    lang = CodingLanguage.PYTHON
    serialized = serializer._serialize(lang)

    assert isinstance(serialized, dict)
    assert serialized["__type__"] == "enum"
    assert serialized["class"] == "CodingLanguage"
    assert serialized["value"] == lang.value

    recovered = serializer._deserialize(serialized)
    assert isinstance(recovered, CodingLanguage)
    assert recovered == lang


def test_list_of_enums_serialize_deserialize(serializer: ColumnStatisticSerializer):
    langs = [CodingLanguage.PYTHON, CodingLanguage.JAVASCRIPT] if len(
        list(CodingLanguage)) > 1 else [CodingLanguage.PYTHON]
    serialized = serializer._serialize(langs)

    assert isinstance(serialized, list)
    assert all(isinstance(e, dict) and e.get(
        "__type__") == "enum" for e in serialized)

    recovered = serializer._deserialize(serialized)
    assert isinstance(recovered, list)
    assert recovered == langs
    assert all(isinstance(e, CodingLanguage) for e in recovered)


def test_dict_enum_to_dataclass_serialize_deserialize(serializer: ColumnStatisticSerializer):
    # map enum -> dataclass
    mapping: Dict[CodingLanguage, WeightedSkills] = {
        CodingLanguage.PYTHON: WeightedSkills("Python", 1.0)
    }
    # if available add another
    langs = list(CodingLanguage)
    if len(langs) > 1:
        mapping[langs[1]] = WeightedSkills("Other", 0.5)

    serialized = serializer._serialize(mapping)
    # keys must be string representations of enums, values dataclass serialized dicts
    assert isinstance(serialized, dict)
    for k, v in serialized.items():
        assert isinstance(k, str)
        assert k.startswith("__enum__:")
        assert isinstance(v, dict) and v.get("__type__") == "dataclass"

    recovered = serializer._deserialize(serialized)
    assert isinstance(recovered, dict)
    # recovered should have enum keys and dataclass values equal to original mapping
    assert recovered == mapping
    for k, v in recovered.items():
        assert isinstance(k, CodingLanguage)
        assert isinstance(v, WeightedSkills)


def test_nested_structure_serialize_deserialize(serializer: ColumnStatisticSerializer):
    nested: Any = [
        {"lang_ratio": {CodingLanguage.PYTHON: 0.8, CodingLanguage.JAVASCRIPT: 0.2}},
        WeightedSkills("React", 0.7),
        {"domains": [FileDomain.CODE, FileDomain.DESIGN] if len(
            list(FileDomain)) > 1 else [FileDomain.CODE]},
    ]

    serialized = serializer._serialize(nested)
    # ensure we serialized nested enums/dataclasses appropriately
    assert isinstance(serialized, list)
    # check inner dicts serialized
    assert isinstance(serialized[0], dict)
    assert "lang_ratio" in serialized[0]
    # keys inside lang_ratio should be string enum keys
    assert all(isinstance(k, str) and k.startswith("__enum__:")
               for k in serialized[0]["lang_ratio"].keys())

    # second element should be a dataclass serialized dict
    assert isinstance(serialized[1], dict) and serialized[1].get(
        "__type__") == "dataclass"

    # third element contains a list of enum serialized values
    assert isinstance(serialized[2], dict)
    domains_serialized = serialized[2]["domains"]
    assert isinstance(domains_serialized, list)
    assert all((isinstance(d, dict) and d.get("__type__") == "enum")
               for d in domains_serialized)

    recovered = serializer._deserialize(serialized)
    assert recovered is not None
    # ensure roundtrip equality for dataclass and enum types inside nested structure
    assert isinstance(recovered, list)
    assert isinstance(recovered[0]["lang_ratio"], dict)
    assert all(isinstance(k, CodingLanguage)
               for k in recovered[0]["lang_ratio"].keys())
    assert isinstance(recovered[1], WeightedSkills)
    assert isinstance(recovered[2]["domains"], list)
    assert all(isinstance(d, FileDomain) for d in recovered[2]["domains"])
