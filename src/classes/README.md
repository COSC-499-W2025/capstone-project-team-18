# Class Structure

## statistic.py

The goal of the design of statistic.py are the following:

1. Have a ground truth list of statistics. This is so we are not messing around with string keys or running into issues where a statistic was changed in one file, but not the other.

2. Have a system, that is reusable and abstract. This allows us to ultize the statistic pattern no matter if we are at the file, project, and user level.

3. Make the code readable and clear.

4. Make the system extendable.

### StatisticTemplate

The statistic template is a description of something we want to measure. For example, for every file we want to be able to measure the last date the file was modified. That is a *type* of statistic. The goal of the StatisticTemplate classes is to repersent that type of statistic in a resuable, DRY way. A type of statistic may be about a one single file, a single project, or about the user's habits.

For example, in the stat we just described, we would create the following StatisticTemplate, and because it is a statistic about a *file* we will create a FileStatisticTemplate (which is different only in name).

```python
statistic_template = FileStatisticTemplate(
    name="DATE_MODIFIED",
    description="last date the file was modified",
    expected_type=date,
)
```

### StatCollection

In our system, we will have to have many different types of statistics. We do not want these templates just floating around in our code. Rather, we want one single place where we can create, delete, modify all of our expected statistics. That is the purpose of the StatCollection classes. They are the ground truth list of statistics.

The advantage of defining statistics this way is:

1. Your IDE will help auto complete your search for a statistic type. When you type "FileStatCollection." all the types of statistics we are measuring about a file will appear.

2. There is no way to incorrectly refer to a type of statistic. Every time we use the statistic "the last date the file was modified" we will always be refering to `FileStatCollection.DATE_MODIFIED.value`.

### Statistic

The last piece of the puzzle is the actual Statistic class. This class is made of two parts, the StatisticTemplate, which describes *what* we are measuring, and the value, which is the actual measured data point. There is nothing special about the Statistic class itself, it is just a holder for these two objects.

Here is an example of creating a Statistic:

We, see that text file has 200 lines of text. So, we create a new statistic as follows:
```python
my_stat = Statistic(FileStatCollection.LINES_IN_FILE.value, 200)
```

### StatisticIndex

This is class is simply a list of Statistic objects. It wraps around a hashmap. Currently, it provides no functionailty. The purpose of this is class is that later down the road we may need to add in a certain functionailty to StatisticIndex (like saving to a database) and that would be very hard without this class.

## report.py

This file describes a FileReport, ProjectReport, and a UserReport.

The FileReport is just a StatisticIndex, which again is just a list of Statistic objects.

A ProjectReport will take many different FileReports and use them to create statistics about a project. For example, we could take the earliest date created file from our FileReports and say create a new statistic about the start date of the project:

```python
    # Get a list of all the created dates in the files
    date_created_list = (report.get(FileStatCollection.DATE_CREATED.value) for report in file_reports)

    # Find the earliest date
    start_date = min(date_created_list)

    #Make a project-level statistic
    project_start_stat = Statistic(ProjectStatCollection.PROJECT_START_DATE.value, start_date)
```

We could even do something more complex, like making a measuring all the lines of *code* (not documentation) written:
```python
# Get all the FileReports on code files
code_file_reports = (report for report in file_reports if report.get(FileStatCollection.TYPE_OF_FILE.value) == FileDomain.CODE)

# For all the code FileReports, sum all of their lines of code up
lines_of_code_written = sum(code_report.get(FileStatCollection.LINES_IN_FILE.value) for code_report in code_file_reports)

# Make a project-level statistic on the lines of code in a project
code_line_stat = Statistic(ProjectStatCollection.LINES_OF_CODE.value, lines_of_code_written)
```

Hopefully these examples also show how to combine all these systems together.


A UserReport will do the same thing as ProjectReport, but with many different ProjectReports.

## Analyzer

See [/analyzer/README.md](../classes/analyzer/README.md)


