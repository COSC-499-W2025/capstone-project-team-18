"""
This file will test the behavior of everything in the statistic.py class
"""
from typing import List
from datetime import date
from src.classes.statistic import *
import pytest


@pytest.fixture()
def stat_template():
    yield StatisticTemplate(
        name="EXAMPLE_STAT",
        description="Example Stat for testing",
        expected_type=int
    )


@pytest.fixture
def skill_weighted_list() -> List[WeightedSkills]:
    return [WeightedSkills("Python", 0.8), WeightedSkills("React", 0.6)]


@pytest.fixture
def sample_date() -> date:
    return date(2024, 1, 1)


def test_statistic_is_type(stat_template: StatisticTemplate):
    with pytest.raises(TypeError):
        Statistic(stat_template, "a")


def test_statistic_value_get(stat_template: StatisticTemplate):
    stat = Statistic(stat_template, 8)
    assert (stat.value == 8)


def test_weighted_skills_creation():
    skill = WeightedSkills(skill_name="Python", weight=0.9)
    assert skill.skill_name == "Python"
    assert skill.weight == 0.9


def test_file_statistic_enum_values():
    assert FileStatisticTemplateCollection.LINES_IN_FILE.value.name == "LINES_IN_FILE"
    assert FileStatisticTemplateCollection.TYPE_OF_FILE.value.expected_type == FileDomain


def test_statistic_valid_int():
    template = FileStatisticTemplateCollection.LINES_IN_FILE.value
    stat = Statistic(template, 150)
    assert stat.value == 150
    assert stat.statistic_template == template
    assert repr(stat) == "<Statistic LINES_IN_FILE=150>"


def test_statistic_valid_enum():
    template = FileStatisticTemplateCollection.TYPE_OF_FILE.value
    stat = Statistic(template, FileDomain.CODE)
    assert stat.value == FileDomain.CODE


def test_statistic_invalid_type_raises():
    template = FileStatisticTemplateCollection.FILE_SIZE_BYTES.value
    with pytest.raises(TypeError):
        Statistic(template, "not_an_int")


def test_statistic_valid_list_of_strings():
    template = FileStatisticTemplateCollection.SKILLS_DEMONSTRATED.value
    stat = Statistic(template, ["Python", "Testing"])
    assert stat.value == ["Python", "Testing"]


def test_add_and_get_statistic(sample_date: date):
    template = FileStatisticTemplateCollection.DATE_CREATED.value
    stat = Statistic(template, sample_date)

    index = StatisticIndex([stat])
    assert len(index) == 1

    retrieved = index.get(template)
    assert retrieved == stat
    assert index.get_value(template) == sample_date


def test_add_overwrites_existing_statistic():
    template = FileStatisticTemplateCollection.LINES_IN_FILE.value
    stat1 = Statistic(template, 100)
    stat2 = Statistic(template, 200)

    index = StatisticIndex([stat1])
    index.add(stat2)

    assert len(index) == 1
    assert index.get_value(template) == 200


def test_get_returns_none_when_missing():
    index = StatisticIndex()
    template = FileStatisticTemplateCollection.DATE_MODIFIED.value
    assert index.get(template) is None
    assert index.get_value(template) is None


def test_to_dict_returns_correct_mapping(sample_date: date):
    stat1 = Statistic(
        FileStatisticTemplateCollection.DATE_CREATED.value, sample_date)
    stat2 = Statistic(FileStatisticTemplateCollection.LINES_IN_FILE.value, 42)

    index = StatisticIndex([stat1, stat2])
    result = index.to_dict()

    assert result == {
        "DATE_CREATED": sample_date,
        "LINES_IN_FILE": 42,
    }


def test_repr_of_statistic_index(sample_date: date):
    stat = Statistic(
        FileStatisticTemplateCollection.DATE_CREATED.value, sample_date)
    index = StatisticIndex([stat])
    rep = repr(index)
    assert "StatisticIndex" in rep
    assert "DATE_CREATED" in rep


def test_project_statistic_collection(skill_weighted_list: List[WeightedSkills]):
    template = ProjectStatisticTemplateCollection.PROJECT_SKILLS_DEMONSTRATED.value
    stat = Statistic(template, skill_weighted_list)
    assert isinstance(stat.value[0], WeightedSkills)
    assert stat.value[0].skill_name == "Python"


def test_user_statistic_collection_dates(sample_date: date):
    template = UserStatisticTemplateCollection.USER_START_DATE.value
    stat = Statistic(template, sample_date)
    assert stat.value == sample_date
