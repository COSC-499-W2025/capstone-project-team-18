# Codebase after the Winter Refactor

## Summary

Over winter break, I refactor the codebase. It is (pretty much) all the same code. Mostly, things are just split into their own files. For example, instead of having one `analyzer.py` file, we have `base_file_analyzer.py`, `c_analyzer.py`, `php_analyzer.py`, etc. In this doc I described what changed and what things to keep in mind moving forward.

### What is this special `__init__.py` \!?\!

Because we are splitting our one file into many, we risk our imports becoming very cumbersome. For example, if we wanted to import the classes `PythonAnalyzer` and `HTMLAnalyzer`, we would need to do

```python
from src.classes.analyzer.html_analyzer import HTMLAnalyzer
from src.classes.analyzer.python_analyzer import PythonAnalyzer
```

Now, with the special `__init__.py` file, all we need to do is this:

```python
from src.classes.analyzer import HTMLAnalyzer, PythonAnalyzer
```

This short hand import is the point of the file.

## Explanation on Specific Sections

### Analyzers

The analyzers are mostly all the same. The only difference being that they are split into their own files.

```
├── analyzer
│   ├── analyzer_util.py (Contains get_appropriate_analyzer and extract_file_reports)
│   ├── base_file_analyzer.py
│   ├── c_analyzer.py
│   ├── code_file_analyzer.py
│   ├── css_analyzer.py
│   ├── html_analyzer.py
│   ├── java_analyzer.py
│   ├── java_script_analyzer.py
│   ├── natural_language_analyzer.py
│   ├── php_analyzer.py
│   ├── python_analyzer.py
│   ├── text_file_analyzer.py
│   └── type_script_analyzer.py
```

The only logical change happens with the new class `SpecificCodeAnalyzer`. This is a super class of all the coding languages (CAnalyzer, PythonAnalyzer, etc). The purpose of this file is that it checks to see if the file is empty before the subclasses, say PythonAnalyzer, analyze the file.

### Report

Reports have changed the most. In our file, project, and user report classes would do some many things, for example ProjectReport would:

- Determine project weight
- Generate Resume Items
- Testing Utils Functions
- Analyze file reports for the following statistics:
  - PROJECT_START_DATE
  - PROJECT_END_DATE
  - USER_COMMIT_PERCENTAGE
  - TOTAL_CONTRIBUTION_PERCENTAGE
  - ACTIVITY_TYPE_CONTRIBUTIONS
  - PROJECT_SKILLS_DEMONSTRATED
  - PROJECT_FRAMEWORKS
  - CODING_LANGUAGE_RATIO
  - IS_GROUP_PROJECT
  - TOTAL_AUTHORS AUTHORS_PER_FILE


So, I took out all of the logic for calculating statistics out of their report classes.

#### New Format

Now, a single logical statistical calculation is separated into its own class. For example, the user report dates are calculated with:
```python
class UserDates(UserStatisticCalculation):
    """
    Calculate earliest user start and latest user end across projects.
    """

    def calculate(self, report: "UserReport") \-\> List\[Statistic\]:
        …

        return \[Statistic(UserStatCollection.USER_START_DATE.value, start_date), Statistic(UserStatCollection.USER_END_DATE.value, end_date)\]
```

Here, all the magic is done in the calculate function. It accepts a UserReport, and then will return a list of statistics about that report.

We have a bunch of these “UserStatisticCalculation” classes that will calculate none, one, or many statistics, and we will combine them all in the \[User/Project\]StatisticReportBuilder class with the `build()` function. This function will calculate all of the statistics and add them to the report. It looks like this:

```python
class UserStatisticReportBuilder(StatisticReportBuilder):
    """Builds user-level statistics by running configured calculators."""

    def __init__(self) \-\> None:
        self.calculators: list\[UserStatisticCalculation\] \= \[
            UserDates(), \# Here is our UserDates example from above
            UserCodingLanguageRatio(),
            UserWeightedSkills(),
        \]

    def build(self, report) \-\> list\[Statistic\]:
        stats: list\[Statistic\] \= \[\]

        for calc in self.calculators:
            new_stats \= calc.calculate(report)
            if new_stats:
                report.statistics.extend(new_stats)
                stats.extend(new_stats)

        return stats
```

Now, UserReport can simply do the following and have all the statistics added:

```python
class UserReport
def __init__(...):
		builder \= UserStatisticReportBuilder()
builder.build(self)
```

#### Adding a New Statistic

To add a new statistic, simply create a new StatisticReportBuilder class which has a calculate() function that accepts a Project/User report, and returns the list of statistics to add. Then add that class to the class variable calculators of the respective StatisticReportBuilder class.

### Testing

Similarly to the other refactors, our testing needs to be organized and sorted. Now, all tests fall into a top level directory (Project discovery, analyzer, resume, etc) and into a specific file. We no longer have a CssAnalyzer test in `tests/analyzer.py` but rather, `tests/analyzer/specific_analyzer/test_css_analyzer.py`.

Also, I went back and added a lot of support for fixtures, or helper functions, for the tests. For example, we would use around three different ways to create a temporary file, but I refactored the tests to always just use the same create temp file function. **Please make sure you are looking for fixtures before making your own\!** Some helpful fixtures already made are:

- Create project/user report from statistics
- Create temp file
- Temporary database
- Some example projects

### Misc

- Please don’t make any more class methods. There is almost always a better place for them.
- Make sure your tests don’t change/create files when run
