# Alex Taschuk Personal Log

[Link to Peer Evaluation](https://prod.teamableanalytics.ok.ubc.ca/courses/174477/peer_evaluations/student/)

## Table of Contents

**[Week 3, Sept. 15–21](#week-3-sept-1521)**

**[Week 4, Sept. 22–28](#week-4-sept-2228)**

**[Week 5, Sept. 29 – Oct. 05](#week-5-sept-29--oct-05)**

**[Week 6, Oct. 06–12](#week-6-oct-6-12)**

**[Week 7, Oct. 07–19](#week-7-oct-0719)**

**[Week 8, Oct. 20–26](#week-8-oct-2026)**

**[Week 9, Oct. 27 – Nov. 02](#week-9-oct-27--nov-02)**

## Week 3, Sept. 15–21

![Peer eval](./log_images/personal_log_imgs/alex/week3.png)

### Recap
This week's goal was to start laying the foundation for our project by discussing potential technologies/the tech stack we want to use, figuring out what each member's strong suit(s) are, and and overall plan of attack for year.

I personally worked on writing the nonfunctional requirements for our requirements document and researching the viability of using Electron for a cross-platform desktop app.

## Week 4, Sept. 22–28

![Peer Eval](./log_images/personal_log_imgs/alex/week4.png)

### Recap
My goals for this week were to work with my team to create the system arcitecture, define specific features for the app, and brainstorm ideas for implementation and unique features that would make our app stand out.

I led our team's brainstorming session and later assigned each person in our team to different parts of the project plan document. My contributions to the document were the proposed solution, the UML use case diagram, some of the use case descriptions, and the tech stack table.

## Week 5, Sept. 29 – Oct. 05

![Peer Eval](./log_images/personal_log_imgs/alex/week5.png)

### Recap
My goals for this week were to support my teammates who were making the DFD and communicate feedback I got from other teams about our diagrams. Additionally, I completed the team log for this week.

## Week 6, Oct. 6-12

![Peer Eval](./log_images/personal_log_imgs/alex/week6.png)

### Recap

With the requirements for Milestone #1 our project needed changes. Sam and I worked together to come up with a new project design that ensured all of these requirements were defined, and reviewed it with the rest of the team to make sure that they agreed/liked the new design. I worked with Erem to update the team's existing level 0 and level 1 DFDs to match the design that Sam and I had come up with. During this process, I was able to clarify/answer the questions that Erem had about the new design. Lastly, I reviewed and approved Sam's PR for the boilerplate class defintions that he created for the project (`analyzer.py`, `report.py`, etc.), and Jimi's personal log for the week.

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
- For each file in a project, we create a `FileReport`, which contains statistics about an individual file (e.g., the file's creation date). Then, we use all of the `FileReports` that make up the project to generate a `ProjectReport`, which contains statistics about an individual project (e.g. the project's creation date (i.e., the earliest file creation date of all of the project's `FileReports`)). Then, we use one or more `ProjectReports` to generate a `UserReport`, which we will use to generate resume items and portfolio items.

With an ORM, we can easily store our `FileReports`, `ProjectReports`, and `UserReports` in the DB. However, there is the issue that during development we will continue to create more statistics that will make up these reports. Since we want each statistic to be a column in our database, we need a function to generate these columns on the fly rather than manually update a DDL on a regular basis. One of the things that I did this week was create `database/utils/init_columns.py`, which contains the functions to do this.

Then, I had to rewrite the fixtures in `test_db.py` that set up a temporary database because the columns in the database were hardcoded rather than generated on the fly.

I also reviewed Erem's PR ([#131](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/131)) and Priyansh's PR ([#132](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/132))