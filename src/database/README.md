# The Database

## Table of Contents

1. [What Data Are We Storing?](#what-data-are-we-storing)
2. [ER Diagram](#er-diagram)
3. [Examples](#example-rows)
    - [3.1 - file_report](#file_report)
    - [3.2 - project_report](#project_report)
    - [3.3 - user_report](#user_report)
    - [3.4 - association_table](#association_table)
4. [SQLAlchemy and Object-Relational Mapping (ORM)](#sqlalchemy-and-object-relational-mapping-orm)
    - [4.1 - Creating Tables](#creating-tables)
    - [4.2 - Adding Rows to a Table](#adding-rows-to-a-table)
    - [4.3 - Getting Rows from a Table](#getting-rows-from-a-table)
5. [Database Configuration](#database-configuration)
    - [5.1 - `db.py`](#dbpy)
        - [5.1.1 - The `Base` Class](#1-the-base-class)
        - [5.1.2 - Defining the Tables](#2-defining-the-tables)
        - [5.1.3 - The `engine`](#3-the-engine)
    - [5.2 - `init_columns.py`](#init_columnspy)
        - [5.2.1 - `_sqlalchemy_type_for()`](#_sqlalchemy_type_for)
        - [5.2.2 - `make_columns()`](#make_columns)
6. [Accessing and Modifying Data: The `Session` Object](#accessing-and-modifying-data-the-session-object)
7. [Connecting the Database to the Rest of the App](#connecting-the-database-to-the-rest-of-the-app)
    - [7.1 - Review: How the App Analyzes Project and Generates Reports](#review-how-the-app-analyzes-project-and-generates-reports)
    - [7.2 - Setting Foreign Keys](#setting-foreign-keys)
    - [7.3 - End Result](#end-result)

## What Data Are We Storing?

The database consists of the following tables:
1. **association_table**: Tracks the bi-directional many-to-many relationship between the *project_report* and *user_report* tables (i.e., track which project reports are used to make which user reports).
2. **file_report**: Stores all `FileReport` objects that are generated. Each row represents a single `FileReport` that is generated for a given file.
3. **project_report**: Stores all `ProjectReport` objects. Each row represents a `ProjectReport` that is generated for a given project using one or more `FileReports`.
4. **user_report**: Stores all user reports. Each row represents a `UserReport` object that is generated using one or more `ProjectReports`.

## ER Diagram

``` mermaid
erDiagram

    FILE_REPORT {
        int id PK
        int project_id FK
        string filepath
        int lines_in_file
        date date_created
        date date_modified
        date date_accessed
        int file_size_bytes
        float ratio_of_individual_contribution
        JSON skills_demonstrated
        JSON type_of_file
        int word_count
        int character_count
        int sentence_count
        float ari_writing_score
        int number_of_functions
        int number_of_classes
        int number_of_interfaces
        JSON imported_packages
    }

    PROJECT_REPORT {
        int id PK
        string project_name
        date project_start_date
        date project_end_date
        JSON project_skills_demonstrated
        bool is_group_project
        int total_authors
        JSON authors_per_file
        float user_commit_percentage
    }

    USER_REPORT {
        int id PK
        date user_start_date
        date user_end_date
        JSON user_skills
    }

    ASSOCIATION_TABLE {
        int project_report_id FK
        int user_report_id FK
    }

    %% Relationships
    FILE_REPORT }o--|| PROJECT_REPORT : "belongs to"
    ASSOCIATION_TABLE }o--|| PROJECT_REPORT : "project"
    ASSOCIATION_TABLE }o--|| USER_REPORT : "user"
```

## Example Rows

### file_report

| id  | project_id | filepath                                          | lines_in_code | date_created               | date_modified              | other columns...   |
| --- | ---------- | ------------------------------------------------- | ------------- | -------------------------- | -------------------------- | ------------------ |
| 1   | 1          | /proj_one/app.py                              | 265           | 2024-11-15 09:45:15.218714 | 2025-03-25 11:53:12.237414 | other statistics...|
| 2   | 2          | /proj_two/src/app/page.tsx                    | 189           | 2024-10-28 10:03:59.187515 | 2024-12-14 15:35:54.564158 | other statistics...|
| 3   | 2          | /proj_two/src/apps/components/navbar/page.tsx | 122           | 2025-03-26 15:13:29.549154 | 2025-07-12 19:43:22.186141 | other statistics...|
| 4   | 3          | /proj_three/clock.py                          | 241           | 2025-01-05 04:48:26.875495 | 2025-10-21 13:51:15.185489 | other statistics...|
| ... | ...        | ...                                               | ...           | ...                        | ...                        | ...                |

- *id*: Primary Key
- *project_id*: Foreign Key to the project that the file is a part of (one-to-many relationship)

### project_report

| id  | project_name    | project_start_date         | project_end_date           | other columns...   |
| --- | --------------- | -------------------------- | -------------------------- | ------------------ |
| 1   | "project-one"   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | other statistics...|
| 2   | "project-two"   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | other statistics...|
| 3   | "project-three" |2025-01-05 04:48:26.875495  | 2025-10-21 13:51:15.185489 | other statistics...|
| ... | ...             | ...                        | ...                        | ...                |

- *id*: Primary Key

### user_report

| id  | user_start_date            | user_end_date              | user_skills                               | other columns...    |
| --- | -------------------------- | -------------------------- | ----------------------------------------- | ------------------- |
| 1   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | ["Python",  "unix"]                       | other statistics... |
| 2   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | ["Python", "Typescript", "Node", "Flask"] | other statistics... |
| ... | ...                        | ...                        | ...                                       | ...                 |

### association_table

| project_report_id | user_report_id |
| ----------------- | -------------- |
| 1                 | 1              |
| 2                 | 2              |
| 3                 | 1              |
| ...               | ...            |

- Project reports with id = 1 and id = 3 were used to create user report with id = 1.
- Project report with id = 2 was used to create user report with id = 2


## SQLAlchemy and Object-Relational Mapping (ORM)

We will be managing a SQLite database using the [SQLAlchemy](https://www.sqlalchemy.org/) library. SQLAlchemy has an Object-Relational Mapper (ORM) component that allows us to define, access, and modify tables in our database in an object-oriented-like way. This is ideal for our use case because the core logic of our app involves using report objects to make higher level report objects (i.e., use several `FileReport` objects to create a `ProjectReport` object, and use several `ProjectReport` objects to create a `UserReport` object.)

### Creating Tables

Suppose we wanted to create a much simpler *file_report* table. In a standard DDL file, we can do this with:

```SQL
CREATE TABLE file_report (
    id         INT,
    project_id INT,
    filepath   VARCHAR(256),
    start_date DATETIME,
    end_date   DATETIME,
    PRIMARY KEY(id)
    FOREIGN KEY (project_id) REFERENCES project_report(id)
)
```

Using SQLAlchemy, we can define the *file_report* table as a class called `FileReportTable`, where the class variables represent the table's columns:

```Python
class FileReportTable(Base):
    __tablename__ = 'file_report' # This is how we define a table's name

    # Create a new column called 'id', then specify its data type and that it is a primary key
    id: Mapped[int] = mapped_column(primary_key=True)  # PK

    # Create a new 'project_id' column with a foreign key reference to the id column in the project_report table
    project_id = Column(Integer, ForeignKey('project_report.id'))

    # This is how we establish a many-to-one relationship with project_report.
    # We can use this to return the project report that is associated with a given file report.
    project_id: Mapped[int] = mapped_column(ForeignKey("project_report.id"))
    project_report: Mapped["ProjectReportTable"] = relationship(back_populates="file_reports")

    # Define the rest of the columns
    filepath = mapped_column(String)
    start_date mapped_column(DateTime)
    end_date = mapped_column(DateTime)
```

**Note**: In practice, we use a `create_columns` function to dynamically create the columns for all of the tables in our database, but we can still access and modify them via ORM (see [5. Database Configuration](#database-configuration))

### Adding Rows to a Table

For this section and the following section ([Getting Rows from a Table](#getting-rows-from-a-table)), we will be using the example tables from the [Examples](#example-rows) section.

Suppose that a `FileReport` object called `fr` is generated after analyzing a very basic Python file which contains the following:

```Python
self.filepath = "/proj_one/app.py"
self.statistics = StatisticIndex([
    Statistic(FileStatCollection.LINES_IN_FILE.value, 265),
    Statistic(FileStatCollection.DATE_CREATED.value, datetime(2024-11-15 09:45:15.218714)), # just assume this is correct
    Statistic(FileStatCollection.DATE_MODIFIED.value, datetime(2025-03-25 11:53:12.237414))
])
```

A standard SQL `INSERT` query to add this data as a row into the *file_report* table for this object would be:

```SQL
INSERT INTO file_report(project_id, filepath, date_created, date_modified)
        VALUES(
                1,
                "/proj_one/app.py",
                265,
                '2024-11-15 09:45:15.218714',
                '2025-03-25 11:53:12.237414'
              )
```

However, with SQLAlchemy this is done a bit differently. Remember that `FileReportTable` class that we just created? We can insert into its table by creating a new `FileReportTable` object and assigning the object the values that we want to insert!

``` Python
with Session(engine) as session: # we'll get to what this is in a bit
    insert_stmt = FileReportTable(
        filepath = fr.filepath,
        fr.get_value(FileStatCollection.LINES_IN_FILE.value),
        fr.get_value(FileStatCollection.DATE_CREATED.value),
        fr.get_value(FileStatCollection.DATE_MODIFIED.value),
    )

    session.add(insert_stmt)
    session.commit()
```

This populates the *file_report* table with:

| id  | project_id | filepath                                          | lines_in_code | date_created               | date_modified              | other columns...   |
| --- | ---------- | ------------------------------------------------- | ------------- | -------------------------- | -------------------------- | ------------------ |
| 1   |            | /proj_one/app.py                              | 265           | 2024-11-15 09:45:15.218714 | 2025-03-25 11:53:12.237414 |                    |

Note: We don't need to specify the *id* variable. SQLAlchemy will automatically increment this for us for each new row.

You may have noticed that the FK reference to the project report with *id = 1* is missing. This is because we don't define the FK just yet, but this will be covered that later.



### Getting Rows from a Table

Suppose we want to get all file reports that were used to create the project report whose *id* is 2. That is, we want these rows:
| id  | project_id | filepath                                          | lines_in_code | date_created               | date_modified              | other columns...   |
| --- | ---------- | ------------------------------------------------- | ------------- | -------------------------- | -------------------------- | ------------------ |
| 2   | 2          | /proj_two/src/app/page.tsx                    | 189           | 2024-10-28 10:03:59.187515 | 2024-12-14 15:35:54.564158 | other statistics...|
| 3   | 2          | /proj_two/src/apps/components/navbar/page.tsx | 122           | 2025-03-26 15:13:29.549154 | 2025-07-12 19:43:22.186141 | other statistics...|


With SQL we can achieve this with:

```SQL
SELECT * FROM file_report WHERE project_id = 2
```

The SQLAlchemy equivalent of this is:

```Python
with Session(engine) as session:
    result = session.execute(
        select(FileReportTable).filter(FileReportTable.project_report_id == 1)
    )
    file_reports = result.scalars().all()
```

- **Note**: This is not the only way to do this using SQLAlchemy. For example, if we wanted to return all file reports that were used to create project reports whose *id* is 2 OR 3:
    - `select_stmt = select(FileReportTable).where(FileReportTable.project_id.in_([2, 3]))`

## Database Configuration

Earlier, we saw how to define and configure tables as classes with SQLAlchemy. Now, let's take a closer look at `db.py` and `init_columns.py`

### `db.py`

The purpose of this file is quite straightforward- define and configure the tables in our database.

There are three main components of this file:
1. The `Base` class
2. Defining the tables
3. The `engine`

#### 1. The `Base` Class

Near the top of our file, we have:

```Python
class Base(DeclarativeBase):
    pass
```

The `DeclarativeBase` class that `Base` extends is SQLAlchemy's root class for creating ORM-mapped classes to standard Python classes (that is, it lets us create tables in an ORM way). We are creating our own `Base` class that extends `DeclarativeBase` so that we (and SQLAlchemy) can keep track of and distinguish our table classes (e.g., `FileReportTable`) from plain regular classes. Classes that extend `Base` also have an `__init__()` method automatically established for them.

**Quick Sidenote**: If needed, we could even customize the `Base` class to add common methods for our tables. For example:

```Python
class Base(DeclarativeBase):
    __abstract__ = True  # this tells SQLAlchemy not to create a table called Base

    id = mapped_column(Integer, primary_key=True) # if we wanted every table to have a PK called id


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns} # get a dict representation of given object

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.to_dict()})>" # str representation of given object
```

#### 2. Defining the Tables

This was already covered in [4. SQLAlchemy and Object-Relational Mapping (ORM)](#sqlalchemy-and-object-relational-mapping-orm).

#### 3. The `engine`

According to the SQLAlchemy [docs](https://docs.sqlalchemy.org/en/20/orm/quickstart.html#create-an-engine),

> The `Engine` is a **factory** that can create new database connections for us, which also holds onto connections inside of a [Connection Pool](https://docs.sqlalchemy.org/en/20/core/pooling.html) for fast reuse.

Simply put, whenever we need a connection to the database somewhere, the `engine` will create that connection for us (it also manages a connection pool for the connections).

In `db.py` there is a `get_engine` function that allows us to easily connect to the database where and whenever we want to. Creating a new engine is as simple as `engine = get_engine()`

**Aside**: `db.py` also has an `init_db` function. This function is unique in that it is only used to populate our `.db` file with the tables and their columns, so it's not something that will be accessed regularly. In fact, once we have a fully functioning app, the only times that it will be called are when the user runs the app for the first time, and any time the app is updated to ensure that database is updated too.

### `init_columns.py`

The `init_columns` file has two functions which work together to dynamically create columns for our tables using the statistic collection classes. For each statistic template in the collections, we get the template's `name` and `expected_type` values. The value stored in the `name` variable directly corresponds to the column's name, and the `expected_type` is used to map the template's type to a valid SQLAlchemy column type.

#### `_sqlalchemy_type_for()`

This is a helper function to `make_columns()`, serving as a bridge from our Python data types and SQLAlchemy column types. One of `StatisticTemplate.expected_type`, `ProjectTemplate.expected_type`, or `UserTemplate.expected_type` should be passed into the function when it is called. It will either return a mapping that is stored in `type_map` (e.g., `_sqlalchemy_type_for(StatisticTemplate.expected_type)` returns `Integer`), or JSON, if the value could not be mapped.

#### `make_columns()`

This is the function that we use to actually make a column.  The function loops through the provided enum collection class (e.g., `ProjectStatCollection), and on each iteration it does the following:
1. Get each statistic template's name and expected type
2. Map the expected type to a SQLAlchemy column type via `_sqlalchemy_type_for()`
3. If the column doesn't already exist, create a new column via `setattr`

## Accessing and Modifying Data: The `Session` Object

The SQLAlchemy [docs](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#what-does-the-session-do) provide a pretty concise explanation of what the `Session` does.

> In the most general sense, the [`Session`](https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session) establishes all conversations with the database and represents a “holding zone” for all the objects which you’ve loaded or associated with it during its lifespan. It provides the interface where SELECT and other queries are made that will return and modify ORM-mapped objects. The ORM objects themselves are maintained inside the [`Session`](https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session), inside a structure called the [identity map](https://docs.sqlalchemy.org/en/20/glossary.html#term-identity-map) - a data structure that maintains unique copies of each object, where “unique” means “only one object with a particular primary key”.

We pass the `engine` into the `Session` as a way to easily connect to the database.

With this understanding let's revisit the example that we saw earlier of how to insert a row into a table:

``` Python
# assume that engine was created via get_engine()...

with Session(engine) as session: # start a new session & connect to the database
    insert_stmt = FileReportTable(
        filepath = fr.filepath,
        fr.get_value(FileStatCollection.LINES_IN_FILE.value),
        fr.get_value(FileStatCollection.DATE_CREATED.value),
        fr.get_value(FileStatCollection.DATE_MODIFIED.value),
    )

    session.add(insert_stmt) # add the row into the current session
    session.commit() # commit the transaction (insert the row into the table)
```

Two things to note about `session.commit()`:
1. We only need to call `session.commit()` if the work we've added in the session modifies or adds data to our database.
2. Since `session.commit()` is used in a Python context managed (i.e., a `with` statement), we don't need to worry about calling `Session.close()` after it because the session is automatically closed at the end of the block.


## Connecting the Database to the Rest of the App

### Review: How the App Analyzes Project and Generates Reports

Now that we have an understanding of what SQLAlchemy is, why we are using it, how our database if configured, and how we access and modify its data, let's take a look at how this is tied in with our app's analysis and report generation.

In `src/app.py` the `start_miner()` function is called to begin the analysis process. First, we get `project_list`, which is a list of `ProjectFile` objects (for $n$ projects, there are $n$ `ProjectFiles` in the list).

We iterate through `project_list`, and for each `ProjectFile`, we get:
- `file_reports`: A list of all `FileReport` objects for a given project
- `pr`: The `ProjectReport` object for the current project in the loop

For each project, `pr` stores the following:
- `self.project_name`
- `self.StatisticIndex` - stores the following statistic templates:
    - `ProjectStatisticTemplate.PROJECT_START_DATE` - earliest created date from `file_reports`
    - `ProjectStatisticTemplate.PROJECT_END_DATE` - latest modified date from `file_reports`
    - `ProjectStatisticTemplate.PROJECT_SKILLS_DEMONSTRATED` - unimplemented
    - `ProjectStatisticTemplate.IS_GROUP_PROJECT` - optional
    - `ProjectStatisticTemplate.TOTAL_AUTHORS` - optional
    - `ProjectStatisticTemplate.AUTHORS_PER_FILE` - optional
    - `ProjectStatisticTemplate.USER_COMMIT_PERCENTAGE` - optional

The resulting `ProjectReport` is appended to the `project_reports` list.

Lastly, we use `project_reports` to create a `UserReport` object. This object stores a list of `ResumeItem` objects (for $n$ projects we have $n$ `ResumeItem` objects in this list) in `self.resume_items`. Each `ResumeItem` stores:
- `self.title` - the project's name
- `self.bullet_points` - a list of bullet points that describe the project
- `self.start_date` - the project's start date
- `self.end_date` - the project's end date

The `UserReport` object also has its own `StatisticIndex` containing the following statistics:
- `UserStatCollection.USER_START_DATE` - earliest start date of all project reports that make up the user report
- `UserStatCollection.USER_END_DATE` - latest end date of all project reports that make up the user report
- `UserStatCollection.USER_SKILLS` - unimplemented

**Note:** *Functionality and documentation on the logic between project reports and user reports is likely to change in the future as we flesh out more details about the user report, resume items, and porfolio items.*


### Setting Foreign Keys

Before we continue, we need to take a look at how foreign keys are going to be created for each row in the *file_report* table. Earlier, when we looked at an example of how to insert a row into the *file_report*, the insert statement did not include a foreign key value, and it should be clear now as to why this was the case: even though we had the `FileReport` objects for the project, we didn't have the project's `ProjectReport` yet, so there was no foreign key to reference!

There are a many ways to approach establishing a FK relation to a row, and it depends on the chosen cascade behavior. For the relationship between *file_report* and *user_report*, we have `cascade="all, delete-orphan"`. The "all" option specifies that we want to use all of the following cascades:
- `save-update`: When you add or merge a project report into the session, all of is children (file reports) are also added to the session.
- `merge`: When you call `session.merge(parent)`, related objects are also merged.
    - `merge()` is used to reassociate a detached object (one that isn't currently in the session) by copying its state into the session.
- `refresh-expire`: Not relevant for us, but for more info, refer to [this](https://docs.sqlalchemy.org/en/20/orm/cascades.html#refresh-expire)
- `expunge`: When you remove a parent from the session, it's children should also be removed
- `delete`: When you delete a parent, its children should also be deleted (i.e., deleting a project report should delete all of its file reports too)

We use "all" in conjunction with "delete-orphan" to indicate that whatever happens to the parent (project reports) should also happen to their children (file reports), and if a child ever becomes disaccociated with its parent, the child should be deleted.

So, when we want to create a FK relation between a bunch of file reports and their project report, we can append the `FileReportTable` objects to the `ProjectReportTable`'s `file_reports` list. With this method, you only need to add the `ProjectReportTable` object to the session.

```Python
with Session(engine) as session:
    project = ProjectReportTable(project_name="proj_one")

    file_one = FileReportTable(filepath="path/to/file_1.py")
    file_two = FileReportTable(filepath="path/to/file_2.py")

    # Append file_one & file_two to the parent's file_reports list
    project.file_reports.append(file_one)
    project.file_reports.append(file_two)

    session.add(project)

    # In addition to adding the project report, SQLAlchemy will
    # automatically add the file reports and set project_id for both of them
    session.commit()
```

For the FK relation between `ProjectReportTable` and `UserReportTable`, our cascade behavior is defined as `cascade="save-update, merge"`. This cascade behavior has more to do with handling session management rather than what to do on deletions because a project report can exist without a user report and vice-versa. Additionally, because we have `secondary=association_table` in the relationship configuration, SQLAlchemy will automatically update the `association_table` with the FK references for us.

### End Result

Now that we have covered FK relationships, and everything else prior to them, we can finally put it all together. Because both FK relationships have a "save-update" cascade behavior, we actually only need to add the user report to the session! This is because SQLAlchemy automatically adds:

- `user_row`, because it was explicitly added
- All project reports in `project_report_rows`, because of the save-update cascade on the many-to-many relationship between `ProjectReportTable` and `UserReportTable`
- All file reports in `file_report_rows`, because of the all cascade (which includes save-update) on the many-to-one relationship between `FileReportTable` and `ProjectReportTable`

```Python
def start_miner(zipped_file: str, email: str = None) -> None:
    """
    This function defines the main application
    logic for the Artifact Miner. Currently,
    results are printed to the terminal

    Args:
        - zipped_file : str The filepath to the zipped file.
    """

    # Unzip the zipped file into temporary directory
    unzipped_dir = tempfile.mkdtemp(prefix="artifact_miner_")
    unzip_file(zipped_file, unzipped_dir)

    project_list = discover_projects(unzipped_dir)
    file_report_rows = []
    project_report_rows = []
    new_user_report_id = get_recent_user_id() + 1 # Get the upcoming user report's id

    with Session(engine) as session:
        # For each project, extract file reports and create ProjectReports
        project_reports = [] # Stores ProjectReport objs
        project_report_rows = [] # Stores ProjectReportTable objs

        for project in project_list:
            file_reports = extract_file_reports(project)

            # Create the rows for the file reports
            file_report_rows = [create_file_report_row(fr) for fr in file_reports] # assume the function returns a new FileReportTable

            pr = ProjectReport(
                project_name=project.name,
                file_reports=file_reports,
                user_email=email
            )
            project_reports.append(pr)

            # Create the row for the project report and set up FK relations
            project_row = create_project_report_row(pr) # assume this returns a new ProjectReportTable
            project_row.file_reports.extend(file_report_rows) # like .append, but for a list of rows
            project_report_rows.append(project_row)


        user_report = UserReport(project_reports)

        user_row = create_user_report_row(user_report) # assume this returns a new UserReportTable
        user_row.project_reports.extend(project_report_rows)

        # add everything to the session and insert the rows into the database
        session.add_all(user_row)
        session.commit()

        print(user_report.to_user_readable_string())

```