# Using Alembic for Database Migration and Database Version Control

## Table of Contents

1. [Explanation](#explanation)
2. [How Alembic Works](#how-alembic-works)
    - [2.1 - Alembic Files](#alembic-files)
    - [2.2 - Generating a Revision File](#generation-a-revision-file)
    - [2.3 - Applying (Upgrading) & Reverting (Downgrading) Revisions](#applying-upgrading--reverting-downgrading-revisions)
3. [Example Workflow](#example-workflow)


## Explanation

**TLDR:** SQLAlchemy does not have built-in support for `ALTER TABLE` operations, which is where a migration library comes in handy. We use Alembic to specify modifications that we want to make to our existing database that allows us to retain its data (or update the data accordingly).

Suppose that we have released a working state of our app for users to install via `pip`. They use it to analyze some of their projects, and generate a resume with it. A few months later, they come back and want to update their resume with some new projects that they have completed. In the meantime, we have updated our app with some changes that modify database functionality.

To keep things simple, let's say that we renamed the `project_name` column in the `project_report` table to `proj_name`. We need a way to implement this change without regenerating the DB because this would wipe the user's existing data.

A simple solution that may appear to work is to check if the database scheme has changed each time the user runs the CLI, and if it has, automatically update the database as needed (e.g., drop a column from a table). However, this is very poor practice that can lead to a wide array of problems, like unintentionally destroying data (AFAIK once you delete data from an SQL database, it cannot be undone.)
- While, realistically, we could probably pull off auto-syncing, it's a really bad practice and this is much safer to implement.

Let's look at an example of where something could go wrong without DB Migration when we renamed a column:

```python
#Before
@make_columns(ProjectStatCollection)
class ProjectReportTable(Base):
    # other table logic...
    project_name = Column(Integer)

#After
@make_columns(ProjectStatCollection)
class ProjectReportTable(Base):
    # other table logic...
    proj_name = Column(Integer)
```

The issue here is that the ORM cannot infer what we mean by this change; it could be anything:
- We renamed `project_name` to `proj_name`.
- We want both columns
- We want to drop old data
- We somehow made a typo

Here's what would happen:
1. The `project_name` col is missing from the model: Drop it
2. The `proj_name` col is missing from the database: Add it

We can use Alembic to specify that we want to change the column's name and retain its data. While this was a very simple example, there are many other problems that auto-syncing can cause.

## How Alembic Works

Alembic allows us to implement version control into our database. This matters when there is a difference of time in the app's development and the user's runtime (i.e., development by us and use of the app from users is not occurring at the same time).

Some terminology:
- Revision: A file that is used to tell Alembic which changes are being made to the database, and how to apply them.

- "Migrate/Migration": The act of applying changes made to the database's schema (SQLAlchemy model) to the database file.

### Alembic Files
```text
capstone-project-team-18/
├── alembic/
│   ├── versions/
│   │   └── 89152a11ba3c_.py (example)
│   ├── env.py
│   ├── README (you are here)
│   └── script.py.mako
├── src/
│   └── database/
│       └── utils/
│           └── db_migrate.py
└── alembic.ini
```

For Alembic’s documentation on its files, see [The Migration Environment](https://alembic.sqlalchemy.org/en/latest/tutorial.html#the-migration-environment).

The `versions/` Directory:
- Contains all of the files generated from `alembic revision --autogenerate -m "commit message"`.

`env.py`:
- A Python script that is run whenever the alembic migration tool is invoked. It contains instructions to configure and generate a SQLAlchemy engine, procure a connection from that engine along with a transaction, and then invoke the migration engine, using the connection as a source of database connectivity.

`script.py.mako`
- Used to generate new migration scripts. Whatever is here is used to generate new files within `versions/`. This is scriptable so that the structure of each migration file can be controlled, including standard imports to be within each, as well as changes to the structure of the `upgrade()` and `downgrade()` functions.
    - It is very unlikely we will ever need to modify this.

`db_migrate.py`
- Contains the `run_migrations()` function, which is called each time the CLI is ran. It runs a command to check if a migration is necessary, and if it is, migrate the database using the most recent revision.

`alembic.ini`
- This is Alembic’s main configuration file.
    - Don't touch this.

### Generation a Revision File

While we continue development, we need to make sure that the database is correctly migrated when users download updates for our app.

After modifying our SQLAlchemy models (e.g., add a new column to `project_report`), we need to run:

```bash
alembic revision --autogenerate -m "commit message"
```

A Python file will be generated in `alembic/versions` (e.g., `89152a11ba3c_.py`). Inside of the file there are two functions:

1. `upgrade():` Contains the logic needed to move the database from the previous revision to this (current) revision. That is, the changes we made to the database.

2. `downgrade():` Contains the logic to revert the changes made with `upgrade()`.

Using the example of adding a column to `project_report`, the `89152a11ba3c_.py` file would look like this:

```Python
"""empty message

Revision ID: 89152a11ba3c
Revises:
Create Date: 2025-12-28 06:29:06.541152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '89152a11ba3c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    new_col = sa.Column('project_test_stat', sa.VARCHAR(), nullable=True)
    op.add_column(table_name='project_report', column=new_col)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('file_report',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('project_id', sa.INTEGER(), nullable=False),
                    sa.Column('filepath', sa.VARCHAR(), nullable=True),
                    sa.Column('lines_in_file', sa.INTEGER(), nullable=True),
                    sa.Column('date_created', sa.DATE(), nullable=True),
                    sa.Column('date_modified', sa.DATE(), nullable=True),
                    sa.Column('file_size_bytes', sa.INTEGER(), nullable=True),
                    sa.Column('ratio_of_individual_contribution',
                              sa.FLOAT(), nullable=True),
                    sa.Column('skills_demonstrated',
                              sqlite.JSON(), nullable=True),
                    sa.Column('type_of_file', sqlite.JSON(), nullable=True),
                    sa.Column('word_count', sa.INTEGER(), nullable=True),
                    sa.Column('character_count', sa.INTEGER(), nullable=True),
                    sa.Column('sentence_count', sa.INTEGER(), nullable=True),
                    sa.Column('number_of_functions',
                              sa.INTEGER(), nullable=True),
                    sa.Column('number_of_classes',
                              sa.INTEGER(), nullable=True),
                    sa.Column('number_of_interfaces',
                              sa.INTEGER(), nullable=True),
                    sa.Column('imported_packages',
                              sqlite.JSON(), nullable=True),
                    sa.Column('percentage_lines_committed',
                              sa.FLOAT(), nullable=True),
                    sa.Column('coding_language', sqlite.JSON(), nullable=True),
                    sa.ForeignKeyConstraint(
                        ['project_id'], ['project_report.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('project_report',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('project_name', sa.VARCHAR(), nullable=True),
                    sa.Column('project_path', sa.VARCHAR(), nullable=True),
                    sa.Column('project_start_date', sa.DATE(), nullable=True),
                    sa.Column('project_end_date', sa.DATE(), nullable=True),
                    sa.Column('project_skills_demonstrated',
                              sqlite.JSON(), nullable=True),
                    sa.Column('is_group_project', sa.BOOLEAN(), nullable=True),
                    sa.Column('total_authors', sa.INTEGER(), nullable=True),
                    sa.Column('authors_per_file',
                              sqlite.JSON(), nullable=True),
                    sa.Column('user_commit_percentage',
                              sa.FLOAT(), nullable=True),
                    sa.Column('total_contribution_percentage',
                              sa.FLOAT(), nullable=True),
                    sa.Column('coding_language_ratio',
                              sqlite.JSON(), nullable=True),
                    sa.Column('total_project_lines',
                              sa.INTEGER(), nullable=True),
                    sa.Column('activity_type_contributions',
                              sqlite.JSON(), nullable=True),
                    sa.Column('project_frameworks',
                              sqlite.JSON(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('proj_user_assoc_table',
                    sa.Column('project_report_id',
                              sa.INTEGER(), nullable=False),
                    sa.Column('user_report_id', sa.INTEGER(), nullable=False),
                    sa.ForeignKeyConstraint(['project_report_id'], [
                        'project_report.id'], ),
                    sa.ForeignKeyConstraint(['user_report_id'], [
                                            'user_report.id'], ),
                    sa.PrimaryKeyConstraint(
                        'project_report_id', 'user_report_id')
                    )
    op.create_table('user_report',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('title', sa.VARCHAR(), nullable=True),
                    sa.Column('user_start_date', sa.DATE(), nullable=True),
                    sa.Column('user_end_date', sa.DATE(), nullable=True),
                    sa.Column('user_skills', sqlite.JSON(), nullable=True),
                    sa.Column('user_coding_language_ratio',
                              sqlite.JSON(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    # ### end Alembic commands ###

```

**IMPORTANT NOTE:** While adding the `--autogenerate` tag may be useful for adding some of the logic to migrate database changes, it _CANNOT DETECT EVERYTHING_, and the file that is generated must be reviewed and likely manually modified.

### Applying (Upgrading) & Reverting (Downgrading) Revisions

When we push the changes (to our repo) for some feature, the Alembic revision file must be included.

#### Applying (Upgrading)

There is a `run_migrations()` function in `db_migrate.py`. This function is called each time the user runs the CLI. It automatically runs `alembic upgrade head`, which migrates the existing database, if necessary, using the most recent revision.

Specifically, `alembic upgrade head` applies all `upgrade()` functions for all revisions that are not yet applied.

For example, we have three revisions in `versions/` (assume their revision numbers are the same as the filename):

1. `rev1.py` (oldest)
2. `rev2.py`
3. `rev3.py` (newest)

After generating rev1, we ran `alembic upgrade head` to migrate with rev1's changes. Later down the line, we made more changes and generated rev2, but never ran `upgrade head`. Even later, we made more changes and generated rev3. When we run `alembic upgrade head` Alembic will first run `rev2.upgrade()`, then it will run `rev3.upgrade()`.

If we want to migrate the database using a specific revision, we can use the revision number in place of `head`.

For example, suppose we have several revisions in `versions/`, and want to migrate using `89152a11ba3c_.py`. This revision's number is `89152a11ba3c`, so we can migrate using this file with

```bash
alembic upgrade 89152a11ba3c
```

It is important to understand that the `upgrade` command is not meant as "Run `upgrade()` functions up to revision `89152a11ba3c`." Alembic interprets it as "Migrate the database to revision `89152a11ba3c`." This means that if revision `89152a11ba3c` is behind the current database's version (i.e., not the head), it will actually use `downgrade()` functions to move the database _down_ to revision `89152a11ba3c`.

#### Reverting (Downgrading)

Suppose that we have five revisions in `versions/` (assume their revision numbers are the same as the filename):

1. `rev1.py` (oldest)
2. `rev2.py`
3. `rev3.py`
4. `rev4.py`
5. `rev5.py` (newest) (current)

We just migrated the database using rev5 via `alembic upgrade head`, but have realized that there is an issue with not only rev5, but also rev4, so we need to revert to rev3. We can do this by running `alembic downgrade rev3`. This tells Alembic to run rev5's `downgrade()` function, to revert the database to rev4, then rev4's `downgrade()` function to revert the database to rev3.

Lastly, reverting to a previous version will not restore that version's data.

#### Recap

| Command                | Effect                            |
| ---------------------- | --------------------------------- |
| `upgrade head`         | Apply all missing upgrades        |
| `upgrade <older>`      | Run downgrades until you reach it |
| `downgrade <rev>`      | Downgrade until that revision     |
| `downgrade -1` (Bonus) | Run one downgrade                 |


## Example Workflow

Let's quickly look a an example migration from start to finish using everything that was just covered.

Suppose we want to add a new column called **test_col** to the `project_report` table. First, we need to add a test_col statistic to our backend logic. To do this, we do the following:

```Python
'''In project_stat_collection.py'''
PROJECT_TEST_STAT = ProjectStatisticTemplate(
    name="PROJECT_TEST_STAT",
    description="A test stat to add as a col to the DB",
    expected_type=str
)
```

```Python
'''In project_statistics.py'''
class ProjectStatisticReportBuilder(StatisticReportBuilder[ProjectReport]):
    """Base builder for project reports."""

    def __init__(self) -> None:
        self.calculators: list[ProjectStatisticCalculation] = [
            ProjectDates(),
            CodingLanguageRatio(),
            ProjectWeightedSkills(),
            ProjectActivityTypeContributions(),
            ProjectAnalyzeGitAuthorship(),
            ProjectTotalContributionPercentage(),
            ProjectTestStat(), # add new column calculator
        ]
    # rest of class...

class ProjectTestStat(ProjectStatisticCalculation):
    # adds this string to every new project report
    def calculate(self, report: ProjectReport) -> list[Statistic]:
        to_return = [
            Statistic(ProjectStatCollection.PROJECT_TEST_STAT.value, "TEST VALUE")]
        return to_return
```

Now, we need a way to add this column to our database. To do this, run `alembic revision --autogenerate -m "added test col"`. This will generate a revision file. The `upgrade()` function will need to be modified to reflect the changes we made to the backend:

```Python
'''Revision file in alembic/versions'''
def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    new_col = sa.Column('project_test_stat', sa.VARCHAR(), nullable=True)
    op.add_column(table_name='project_report', column=new_col)
    # ### end Alembic commands ###
```
