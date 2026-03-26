from src.core.statistic import (
    Statistic, UserStatCollection, CodingLanguage
)
from src.core.portfolio.builder.concrete_builders import (
    UserDateSectionBuilder
)
from datetime import date


def test_to_user_readable_string(user_report_from_stats):
    lang_ratio = {CodingLanguage.PYTHON: 0.8528,
                  CodingLanguage.CSS: 0.1002, CodingLanguage.TYPESCRIPT: 0.0470}
    stats = [
        Statistic(UserStatCollection.USER_START_DATE.value, date(2023, 9, 20)),
        Statistic(UserStatCollection.USER_END_DATE.value,
                  date(2025, 10, 20)),
        Statistic(UserStatCollection.USER_CODING_LANGUAGE_RATIO.value, lang_ratio),
    ]
    report = user_report_from_stats(stats)

    date_builder = UserDateSectionBuilder()

    date_section = date_builder.build(report)

    date_output = date_section.render() if date_section else ""

    assert "You started your first project on 9/20/2023!" in date_output
    assert "Your latest contribution was on 10/20/2025." in date_output


def test_to_user_readable_string_empty(user_report_from_stats):
    report = user_report_from_stats([])

    date_builder = UserDateSectionBuilder()
    # All builders should return None when there's no data
    assert date_builder.build(report) is None
