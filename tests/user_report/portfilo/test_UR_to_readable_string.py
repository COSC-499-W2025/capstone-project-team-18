from src.classes.statistic import (
    StatisticIndex, Statistic, StatisticTemplate,
    UserStatCollection, CodingLanguage
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
    out = report.to_user_readable_string()
    print(out)
    assert "You started your first project on 9/20/2023!" in out
    assert "Your latest contribution was on 10/20/2025." in out
    assert "Your coding languages: Python (85%), CSS (10%), Typescript (4%)"
    # assert "Your skills include: " in out


def test_to_user_readable_string_empty(user_report_from_stats):
    report = user_report_from_stats([])
    assert report.to_user_readable_string() == "No user statistics are available yet."


def test_to_user_readable_string_fallback_generic_title_value(user_report_from_stats):
    dummy_template = StatisticTemplate(
        name="CUSTOM_UNKNOWN_STAT",
        description="A stat not covered by custom phrasing",
        expected_type=int,
    )
    idx = StatisticIndex([Statistic(dummy_template, 42)])
    report = user_report_from_stats(idx)
    out = report.to_user_readable_string()
    assert "Custom Unknown Stat: 42" in out
