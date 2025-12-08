# Alex Taschuk Personal Log

## Table of Contents

**[Week 3, Sept. 15–21](#week-3-sept-1521)**

**[Week 4, Sept. 22–28](#week-4-sept-2228)**

**[Week 5, Sept. 29 – Oct. 05](#week-5-sept-29--oct-05)**

**[Week 6, Oct. 06–12](#week-6-oct-6-12)**

**[Week 7, Oct. 07–19](#week-7-oct-0719)**

**[Week 8, Oct. 20–26](#week-8-oct-2026)**

**[Week 9, Oct. 27 – Nov. 02](#week-9-oct-27--nov-02)**

**[Week 10, Nov. 03 – 09](#week-10-nov-03--nov-09)**

**[Week 11, Nov. 10 – 16](#week-11-nov-10--nov-16)**

**[Week 12, Nov. 17 – 23](#week-12-nov-17--nov-23)**

**[Week 13, Nov. 24 – 29](#week-13-nov-24--nov-29)**

**[Week 14, Nov. 30 – Dec. 07](#week-14-nov-30--dec-07)**

****

## Week 3, Sept. 15–21

![Peer eval](./log_images/personal_log_imgs/alex/week3.png)

### Recap
This week's goal was to start laying the foundation for our project by discussing potential technologies/the tech stack we want to use, figuring out what each member's strong suit(s) are, and and overall plan of attack for year.

I personally worked on writing the nonfunctional requirements for our requirements document and researching the viability of using Electron for a cross-platform desktop app.

## Week 4, Sept. 22–28

![Peer Eval](./log_images/personal_log_imgs/alex/week4.png)

### Recap
My goals for this week were to work with my team to create the system architecture, define specific features for the app, and brainstorm ideas for implementation and unique features that would make our app stand out.

I led our team's brainstorming session and later assigned each person in our team to different parts of the project plan document. My contributions to the document were the proposed solution, the UML use case diagram, some of the use case descriptions, and the tech stack table.

## Week 5, Sept. 29 – Oct. 05

![Peer Eval](./log_images/personal_log_imgs/alex/week5.png)

### Recap
My goals for this week were to support my teammates who were making the DFD and communicate feedback I got from other teams about our diagrams. Additionally, I completed the team log for this week.

## Week 6, Oct. 6-12

![Peer Eval](./log_images/personal_log_imgs/alex/week6.png)

### Recap

With the requirements for Milestone #1 our project needed changes. Sam and I worked together to come up with a new project design that ensured all of these requirements were defined, and reviewed it with the rest of the team to make sure that they agreed/liked the new design. I worked with Erem to update the team's existing level 0 and level 1 DFDs to match the design that Sam and I had come up with. During this process, I was able to clarify/answer the questions that Erem had about the new design. Lastly, I reviewed and approved Sam's PR for the boilerplate class definitions that he created for the project (`analyzer.py`, `report.py`, etc.), and Jimi's personal log for the week.

## Week 7, Oct. 07–19

![Peer Eval](/logs/log_images/personal_log_imgs/alex/week7.png)

### Recap

This week, I began created a simple CLI tool which the user will use to do things such as specify their project's filepath, give their permission for the program to access their files, and to start the artifact mining process.
- The PR for this feature can be found [here](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/37)

Additionally, I implemented logic for a function that will parse metadata that will be present in every file, such as the file's creation date. This PR included the feature, test cases for the feature, and documentation.
- The PR can be found [here](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/47)

I met with my team and we planned expectations and tasks for the next coming weeks. We talked about what features we wanted to work on and who would do what. Lastly, I reviewed a [PR](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/44) which closed issue #43, and a [PR](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/46) which closed issue #45.

## Week 8, Oct. 20–26

![Peer Eval](/logs/log_images/personal_log_imgs/alex/week8.png)

### Recap

This week, my goal was to initialize our app's database.

I completed issue [#80](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/80), which adds all of the code for the database's initialization and test cases for it. We will be accessing and modifying the DB using the `sqlalchemy` library. There are a few new issues that will need to be opened to flesh out some specifics about the DB (e.g., complete documentation for the DB and how to access/modify tables and implement columns that will be stored in the user_report table.)

I also reviewed Sam's PR ([#88](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/88)) and Priyansh's PR ([#84](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/67))


## Week 9, Oct. 27 – Nov. 02

![Peer Eval](/logs/log_images/personal_log_imgs/alex/week9.png)

### Recap

This week, my goal was to continue working on database integration with the backend of our app. There are two main tasks that are required to do this:

1. Dynamically generate the columns of our DB's tables using the statistics that we store in `FileStatCollection`, `ProjectStatCollection`, and `UserStatCollection`.
2. FileReports, ProjectReports, and UserReports should be added to the database when they are created. This should be done at the end of the mining process to ensure that all relationships between the projects are established. (This is my next goal)

I completed issue [#128](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/128), which describes task #1. The PR for this issue is [#135](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/135). While the task sounds simple, there was a lot that had to go into it.

The reason that we are using SQLAlchemy for DB management is that it is an Object Relational Mapper (ORM), which allows us to access and modify our SQLite database in an object-oriented way. This is useful because of the way that we are generating information about a user's projects:
- For each file in a project, we create a `FileReport`, which contains statistics about an individual file (e.g., the file's creation date). Then, we use all of the `FileReports` that make up the project to generate a `ProjectReport`, which contains statistics about an individual project (e.g. the project's creation date (i.e., the earliest file creation date of all of the project's `FileReports`)). Then, we use one or more `ProjectReports` to generate a `UserReport`, which we will use to generate rèsumè items and portfolio items.

With an ORM, we can easily store our `FileReports`, `ProjectReports`, and `UserReports` in the DB. However, there is the issue that during development we will continue to create more statistics that will make up these reports. Since we want each statistic to be a column in our database, we need a function to generate these columns on the fly rather than manually update a DDL on a regular basis. One of the things that I did this week was create `database/utils/init_columns.py`, which contains the functions to do this.

Then, I had to rewrite the fixtures in `test_db.py` that set up a temporary database because the columns in the database were hardcoded rather than generated on the fly.

I also reviewed Erem's PR ([#131](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/131)) and Priyansh's PR ([#132](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/132))

## Week 10, Nov. 03 – Nov. 09

![Peer Eval](/logs/log_images/personal_log_imgs/alex/week10.png)

### Recap

This week, I wrote a large and concise document on our database, including:
- The database's structure,
- Example rows for each table
- What SQLAlchemy is, what an ORM is, and how to read/write to tables
- The database's configuration:
    - The `Base` class
    - Defining the tables
    - The `engine`
    - Initializing columns in a dynamic way
- Using the `session` object
- Connecting the database to the rest of our app

Additionally, while doing research to make sure that the document was as correct and concise as possible, I learned a lot more about SQLAlchemy, like the fact that I had to one-to-many relationship between the `project_report` and `file_report` table incorrectly configured.

As a result, I ended up rewriting some of the table-defining logic in `db.py`, and I had to rewrite some of the initialization stage of the test cases for the database.

The PR for this feature is [#159](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/159)

I also moved the `/database` directory into the `/src` directory and made sure that all functionality (imports, etc.) was updated accordingly.
- The PR for this is [#154](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/154)

Lastly, I reviewed Sam's PR [#155](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/155), and Priyansh's PR [#170](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/170).

## Week 11, Nov. 10 – Nov. 16

Reading week; nothing to log.

## Week 12, Nov. 17 – Nov. 23

### Peer Eval

![Peer Eval](/logs/log_images/personal_log_imgs/alex/week12.png)


### Recap

This week, I spent a lot of time preparing and working on the final changes and requirements for Milestone 1.

Firstly, I created PR, [#185](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/185), which closed issue [#148](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/148). The PR ties in our app's backend logic with the database. This includes logic to read, for example, a `FileReport` object and writes it as a row to the `file_report` table.

My second PR, [#207](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/207), added additional statistics:
- `AVG_ARI_WRITING_SCORE`: The average score of all files with an ARI_WRITING_SCORE statistic that are in the project
- `USER_ARI_WRITING_SCORE`: The average score of all projects with an AVG_ARI_WRITING_SCORE statistic that make up the UserReport.
    - In addition to a calculation function, I also added logic to print this in the `to_user_readable_string()` function.
- `USER_CODING_LANGUAGE_RATIO`: The ratio of each coding language that is present in one or more `ProjectReports`
    - Note: This is currently wrong and I need help figuring out how to correctly calculate the ratios
    - In addition to a calculation function, I also added logic to print this in the `to_user_readable_string()` function.

My third PR, [#232](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/232), is to add test logic for the `USER_CODING_LANGUAGE_RATIO` statistic in my second PR. It is currently only a draft PR because the logic to calculate the statistic is inaccurate; I'm waiting for the issue to fix the bug to be closed before I publish the PR.

My fourth PR, [#236](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/236), was to close a sub-issue for a larger issue for the feature for the user to retrieve rèsumè bullet points from previously generated project reports. The logic for this includes two functions:
- `get_project_from_project_name()`: Takes a project's name, finds the corresponding row in the database, and converts the row to a `ProjectReport` object. This will be used when the user wants to retrieve/print a rèsumè bullet point for a project they have already analyzed.
- `get_file_reports()`: A helper function for the former. When we create a new `ProjectReport` object, we need to give it a list of the `FileReports` that make up the project report. This function uses the FK relation between the `project_report` and `file_report` to read all of the rows in `file_report` and generate a list of `FileReport` objects.

Additionally, I spent time making issues for the final changes that needed to be made/implemented before Milestone 1 is due for other team members to assign themselves to.

Lastly, I reviewed the following PRs:
- [#191: Fixed Issue 187, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/191)
- [#199: Improve cross-platform file path normalization, Priyansh](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/199)
- [#206: Created Project-Level Weighted skills Statistic, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/206)
- [#226: Added feature for deleting user reports and related data by either id, title, or zipped files, Priyansh](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/226)
- [#227 Git Projects Use Git Stats instead of File Metdata, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/227)

## Week 13, Nov. 24 – Nov. 29

### Peer Eval

![Peer Eval](/logs/log_images/personal_log_imgs/alex/week13.png)

### Recap

This week, I spent time making ensuring the deliverables for Milestone 1 will be done in time. I also worked on finishing open issues that were assigned to me.

**Issues/PRs**

[#254 - created function to get UserReport from database](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/254): This PR contributed towards Requirement 14, which is that the user can retrieve previously generated portfolio items. The PR included a function which would accept the name of a `UserReport`, retrieve the row in the `user_report` table with the corresponding value, convert the row to a `UserReport` object and return it.

[#265 - Rank ProjectReports by weight](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/265): This PR completes Requirement 17, which is to summarize the top rank projects. I made changes to the `__init__` function in the `UserReport` class to sort the object's list of `ProjectReports` according to each report's weight.

[#272 - dynamically generate resume and portfolio header lengths](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/272): This PR improved the formatting of résumé and portfolio items that are printed to the CLI.

[#268 - Milestone 1 Team Contract](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/268): I wrote up the team contract for our team and had everyone review and sign it before merging the PR.

Additionally, I began working on issue [#166](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/166), which is a refactoring issue to create global and non-global fixtures that our pytests can use. To be specific, I wrote a fixture for the `test_analyzer_git_methods.py` file along with some helper functions. I then rewrote all of the tests within this file to use the new fixtures and helper functions.

Here are the PRs that I reviewed this week:

- [#223: store user preferences as json - PR #3: Advanced Preferences & View System, Erem](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/223)
- [#242: Fix coding language ratio calculation by filtering duplicate files and venv files, Erem](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/242)
- [#245: Aggregate `git blame` stats for project overview, Jimi](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/245)
- [#260: 216 b create cli menu option to delete a user report, Erem](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/260)
- [#263: ProjectReport Clean up `__init__`, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/263)

## Week 14, Nov. 30 – Dec. 07

### Peer Eval

![Peer Eval](/logs/log_images/personal_log_imgs/alex/week14.png)

### Recap

This week, I worked on fixing bugs that were crucial to completing all of the requirements for Milestone 1. I also updated our app's README on the `main` branch, which included updating the app's documentation, writing the milestone 1 team contract, updating and adding the DFDs, updating and adding the app's system architecture, and adding the milestone 1 feature checklist. Additionally, I recorded our team's demo video for this milestone. Additionally, I began refactoring how we use the user's preferences when generating file reports, but I did not complete it feature so there is no PR for it yet.

**Issues/PRs**

[#285 - Update readme documentation for milestone 1](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/285): This PR has all changes to our `README.md` on the `main` brnach.

[#302 - Write stats to tables](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/302): This PR made several important changes to reading and writing to/from our database. There were several statistics that were not being written to the database upon a new `ProjectReport` and/or `UserReport` being generated, and some statistics were not being included when retrieving a rèsumè bullet point (`ProjectReport`) or portfolio (`UserReport). The issue with retrieving data was in part due to the issue with writing data, but there were also issue with how we retrieved data which were solved by this PR.

Here are the PRs I reviewed this week:
- [#267: add tqdm progress bars for anaylsis, Erem](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/267)
- [#290: Expand upon User Skills, Jimi](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/290)
- [#294: Removed Ari-Writing-Score User Skills, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/294)
- [#304: Added missing promp for naming portfolio in CLI, Priyansh](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/304)
- [#307: Empty Project Report Handling, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/307)
- [#308: Added New Statistic Framework, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/308)
- [#309: Put Chronological Skills and Projects in the Portfolio, Sam](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/309)
