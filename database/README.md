# UPDATE THE MERMAID DIAGRAM


# The Database

## What Data Are We Storing?

The database consists of the following tables:
1. **association_table**: Tracks the bi-directional many-to-many relationship between the *project_report* and *user_report* tables.
2. **file_report**: Stores all `FileReport` objects that are generated. Each row represents a single `FileReport` that is generated for a given file.
3. **project_report**: Stores all `ProjectReport` objects. Each row represents a `ProjectReport` that is generated for a given project using one or more `FileReports`.
4. **user_preferences**: Stores the preferences that the user chooses prior to generating a report.
    - Currently, this is structured such that the table will only contain a single row, with each column storing an optional user preference (e.g., *files_to_ignore*, which is a list of file extensions to ignore). There is a probably a better way to keep the user's choices persistent between sessions but I'm not sure how it could be done. I might reach out to Ramon and ask for advice.
5. **user_report**: Stores all user reports. Each row represents a `UserReport` object that is generated using one or more `ProjectReports`.

## ER Diagram

``` mermaid
erDiagram

    USER_PREFERENCES {
        int id PK
        boolean consent
        JSON files_to_ignore
        date file_start_time
        date file_end_time
    }

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
        float ari_writing score
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
    PROJECT_REPORT ||--o{ FILE_REPORT : "has many"
    PROJECT_REPORT ||--o{ ASSOCIATION_TABLE : "linked to users"
    USER_REPORT ||--o{ ASSOCIATION_TABLE : "linked to projects"
```

# Examples

### user_preferences

| id  | consent | files_to_ignore          | file_start_time     | file_end_time       |
| --- | ------- | ------------------------ | ------------------- | ------------------- |
| 1   | True    | [".md", ".yml", ".json"] | 2023-04-04 00:00:00 | 2023-05-31 11:59:59 |

### file_report


| id  | project_id | filepath                                          | lines_in_code | date_created               | date_modified              | other columns...   |
| --- | ---------- | ------------------------------------------------- | ------------- | -------------------------- | -------------------------- | ------------------ |
| 1   | 1          | /tmp/proj_one/app.py                              | 265           | 2024-11-15 09:45:15.218714 | 2025-03-25 11:53:12.237414 | other statistics...|
| 2   | 2          | /tmp/proj_two/src/app/page.tsx                    | 189           | 2024-10-28 10:03:59.187515 | 2024-12-14 15:35:54.564158 | other statistics...|
| 3   | 2          | /tmp/proj_two/src/apps/components/navbar/page.tsx | 122           | 2025-03-26 15:13:29.549154 | 2025-07-12 19:43:22.186141 | other statistics...|
| 4   | 3          | /tmp/proj_three/clock.py                          | 241           | 2025-01-05 04:48:26.875495 | 2025-10-21 13:51:15.185489 | other statistics...|
| ... | ...        | ...                                               | ...           | ...                        | ...                        | ...                |

- *id*: Primary Key
- *project_id*: Foreign Key to the project that the file is a part of (one-to-many relationship)

### project_report

| id  | project_start_date         | project_end_date           | other columns...   |
| --- | -------------------------- | -------------------------- | ------------------ |
| 1   | 2024-06-13 10:32:16.489461 | 2025-10-25 02:59:13.556961 | other statistics...|
| 2   | 2024-06-19 13:04:46.782516 | 2025-09-18 00:10:32.587164 | other statistics...|
| 3   | 2025-01-05 04:48:26.875495 | 2025-10-21 13:51:15.185489 | other statistics...|
| ... | ...                        | ...                        | ...                |

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

## SQLAlchemy and Object-Relational Mapping

We will be managing a SQLite database using the [SQLAlchemy](https://www.sqlalchemy.org/) library. SQLAlchemy has an Object-Relational Mapper (ORM) component that allows us to access and modify the database in an object-oriented-like way. This is ideal for our use case because the core logic of our app involves using report objects to make higher level report objects (i.e., use several `FileReport` objects to create a `ProjectReport` object, and use several `ProjectReport` objects to create a `UserReport` object.)

- Include example of getting data via traditional SQL vs using SQLAlchemy

## Database Configuration

Explain how `db.py` works with `create_columns.py`

## Accessing and Modifying Data

Explain and give examples of getting and changing data

## Connecting the Database to the Rest of the App

Explain how we (will) actually utilize the database