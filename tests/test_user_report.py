from datetime import date
from classes.statistic import (
    StatisticIndex, Statistic,
    UserStatCollection, WeightedSkills
)
from classes.report import UserReport

def test_to_user_readable_string():
    idx = StatisticIndex([
        Statistic(UserStatCollection.USER_START_DATE.value, date(2023, 9, 20)),
        Statistic(UserStatCollection.USER_END_DATE.value,   date(2025, 10, 20)),
        Statistic(UserStatCollection.USER_SKILLS.value, [
            WeightedSkills("Python", 0.9),
            WeightedSkills("Pandas", 0.7),
            WeightedSkills("SQL", 0.6),
        ]),
    ])
    report = UserReport.from_statistics(idx)
    out = report.to_user_readable_string()
    assert "You started your first project on 9/20/2023!" in out
    assert "Your latest contribution was on 10/20/2025." in out
    assert "Your skills include: " in out