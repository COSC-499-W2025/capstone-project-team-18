# CLI User Guide

## Table of Contents

1. [CLI Tool: Project Artifact Miner](#project-artifact-miner-a-cli-tool)
    - [1.1 Quickstart](#quick-start)
    - [1.2 CLI Command Quick Reference](#cli-command-quick-reference)
    - [1.3 Workflow](#workflow)
    - [1.4 Testing](#testing)
3. [Milestone 1 Documentation](#milestone-1-documentation)
    - [2.1 Team Contract](#team-contract)
    - [2.2 Diagrams](#diagrams)
    - [2.3 Requirements Checklist](#requirements-checklist)

# Project Artifact Miner: A CLI Tool

We are building a command‑line interface (CLI) tool for mining project artifacts. The CLI entrypoint lives in `/src/app.py` and uses Python's standard `cmd` module to provide an interactive system for the user.

## Quick Start

Prerequisites: Python 3.11+ recommended.

1. Clone this repository locally

2. Either open the repository in a dev container using VS Code, or in a virtual environment. To configure a virtual environment:
    1. `cd` to the repository
    2. run `python3 -m venv venv`
    3. activate the venv with `source venv/bin/activate`
    4. install necessary libraries and dependencies with `pip install -r requirements.txt`

3. Start the app with `python -m src.app`. The CLI tool will run and you will see the main menu followed by the `(PAF)` prompt.
    - To create portfolio and/or résumé items, you must, at a minimum, provide consent for the analyzer to parse the folders and files you provide, and the filepath to a zipped/compressed folder that contains the project(s) you want analyzed

## CLI Command Quick Reference


| Option                                        | Description                                                                                                                                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `1` Permissions                               | Give or deny consent to access folders/files in the provided filepath                                                                                                                                   |
| `2` Set Filepath                              | Give the path to the zipped/compressed directory containing one or more projects                                                                                                                                      |
| `3` Begin Artifact Miner                      | Begin analyzing projects and building résumé & portfolio items                                                                                                                                          |
| `4` Configure Email for Git Stats             | Give the email associated with your GitHub account to gather git-related statistics                                                                                                                     |
| `5` User Logic (Name & Password)              |                                                                                                                                                                                                         |
| `6` Configure Preferences                     | Provide custom configurations prior to analysis                                                                                                                                                         |
| `7` View Current Preferences                  | View the current state of each preference                                                                                                                                                               |
| `8` Delete a Portfolio                        | Delete a portfolio item from the database by selecting from the list of existing portfolios, providing a portfolio name, or using the portfolio of the zip file most recently analyzed.                 |
| `9` Retrieve a Portfolio                      | Retrieve a portfolio item from the database by selecting from the list of existing portfolios, providing a portfolio name, or using the portfolio of the zip file most recently analyzed.               |
| `10` Get resume bullet point | Retrieve a résumé bullet point by selecting a project from the database, from the list of existing projects, providing a portfolio name, or using the portfolio of the zip file most recently analyzed. |
| `back`/`cancel` | Return to previous page or main menu
| `exit`/ `ctrl + c` | exit application

## Workflow

### 0. Main Menu
```
=== Artifact Miner Main Menu ===
Choose one of the following options:
(1) Permissions
(2) Set filepath
(3) Begin Artifact Miner
(4) Configure Email for Git Stats
(5) User Login (Name & Password)
(6) Configure preferences
(7) View current preferences
(8) Delete a Portfolio
(9) Retrieve a Portfolio
(10) Get resume bullet point
Type 'back' or 'cancel' to return to this main menu
Type help or ? to list commands
```
- `back`/`cancel` can be used at any point to return the user to the previous screen or to the main menu.

### 1. Permissions
```
(PAF) 1
Do you consent to this program accessing all files and/or folders
in the filepath you provide and (if applicable) permission to use
the files and/or folders in 3rd party software?
(Y/N) or type 'back'/'cancel' to return to main menu: Y
```
- `Y` = Grant access
- `N` = Deny, exit app


### 2. Filepath
```
(PAF) 2
Paste or type the full filepath to your zipped project folder: (or 'back'/'cancel' to return):
/path/to/projects.zip
```
- Enter any valid filepath to a compressed directory

### 3. Begin
```
(PAF) 3
Beginning analysis of: /path/to/projects.zip
------------Resume------------
For N projects in the filepath
there are N resume bullet points
------------------------------

-------------Portfolio-------------
For each zipped project folder, one
portfolio item is created
-----------------------------------
Enter a name for your portfolio (leave blank to keep 'projects'): my_portfolio

```
- Requires steps `1` & `2` to be completed first; steps `4` and `6` are optional.


### 4. Email Configuration
```
(PAF) 4
By providing your email, you give consent for the application to analyze all information stored by Git.
If you don't wish to consent, enter 'x' to revoke permissions
Enter the email you use for your Git/GitHub account: spencer@example.com
```
- The email address should match the email that is associated with the user's Git/GitHub account that their contribution corresponds to.


### 5. User Login
```
Enter your login credentials:
Enter your name: (or 'back'/'cancel' to return): Spencer
Enter your password: (or 'back'/'cancel' to return): password
```
- Note: This feature will be fleshed out more in the following semester

### 6. Configure Preferences
```
(PAF) 6

=== Preferences Configuration ===
(1) Configure Date Range Filtering
(2) Configure Files to Ignore
(3) Reset to Defaults
(4) Back to Main Menu
Select option (1-4), or 'exit'/'quit' to close app: [1-4]
```

#### 6.1 Configure Date Range Filtering
```
Select option (1-4), or 'exit'/'quit' to close app: 1

Configure date range for file filtering (YYYY-MM-DD format)
Enter start date (or 'skip' for no limit): 2024-12-01
Enter end date (or 'skip' for no limit): 2025-12-01
```
- Only files whose created or modified date metadata that is within the given range will be analyzed.

#### 6.2 Configure Files to Ignore
```
Select option (1-4), or 'exit'/'quit' to close app: 2

Configure file extensions to ignore during analysis
Enter extensions separated by commas (e.g., .log, .tmp, .cache)
Extensions to ignore (or 'clear' to remove all): .cache, .py, .java
```

#### 6.3 Reset to Defaults
```
Select option (1-4), or 'exit'/'quit' to close app: 3

Reset ALL preferences to defaults? This cannot be undone. (Y/N): Y
```

#### 6.4 Back to Main Menu
```
Select option (1-4), or 'exit'/'quit' to close app: 4

=== Artifact Miner Main Menu ===
(1) Permissions
    ...
```
- Equivalent to `cancel`


### 7. View Current Preferences
```
(PAF) 7

=== Current Configuration ===
User Consent: ✓ Granted
Project Filepath: /absolute/path/to/projects.zip
User Name: Not set
User Email: spencer@example.com
Date Range: 2024-12-01 to 2025-12-01
Ignored Extensions: .cache, .py, .java
Last Updated: 2025-12-01T16:11:53.352974
Preferences File: /Users/spencer/Desktop/capstone-project-team-18/src/database/preferences.json

Press '6' to configure preferences, or 'back'/'cancel' to return to main menu: 6

=== Preferences Configuration ===
(1) Configure Date Range Filtering
    ...
```

### 8. Delete a Portfolio
```
(PAF) 8

=== Delete Portfolio ===
You can delete a portfolio by:
  1. Select from list of existing portfolios
  2. Enter portfolio name (or press Enter to use preferences)

Enter your choice (1-2) or portfolio name (or 'back'/'cancel' to return):
```

#### 8.1 Select from Existing Portfolios
```
Enter your choice (1-2) or portfolio name (or 'back'/'cancel' to return): 1

=== Existing Portfolios ===
(1) my_portfolio
    Projects: 2

(2) old_projects
    Projects: 4

(3) personal_projects
    Projects: 4

Select portfolio (1-3), 'back'/'cancel' to return, or 'exit'/'quit' to close app: 2

Found portfolio: old_projects
Associated projects: 4

Are you sure you want to delete this portfolio? (Y/N): y
```

#### 8.2 Enter Portfolio Name
```
Enter your choice (1-2) or portfolio name (or 'back'/'cancel' to return): 2

TODO: finish this once it is fixed
```

### 9. Retrieve a Portfolio
```
(PAF) 9

=== Retrieve Portfolio ===
You can retrieve a portfolio by:
  1. Select from list of existing portfolios
  2. Enter portfolio name (or leave blank to use last analyzed)

Enter your choice (1-2), portfolio name, or leave blank for last analyzed (or 'back'/'cancel' to return):
```

#### 9.1 Select from Existing Portfolios
```
Enter your choice (1-2), portfolio name, or leave blank for last analyzed (or 'back'/'cancel' to return): 1

=== Existing Portfolios ===
(1) my_portfolio
    Projects: 2

(2) old_projects
    Projects: 4

(3) personal_projects
    Projects: 4

Select portfolio (1-3), 'back'/'cancel' to return, or 'exit'/'quit' to close app: 2
-------------Portfolio-------------
...
-----------------------------------
```

#### 9.2 Enter Portfolio Name
```
Enter your choice (1-2), portfolio name, or leave blank for last analyzed (or 'back'/'cancel' to return): 2
Enter portfolio name: personal_projects
-------------Portfolio-------------
...
-----------------------------------
```

### 10 Get Résumé Bullet Point
```
(PAF) 10

=== Get Resume Bullet Point ===
Project name (or 'back'/'cancel' to return): projectA

Generated resume bullet point(s):
...
```
- `projectA` is a project folder within the `personal_projects` portfolio


### `help` / `?`
```
(PAF) help

Documented commands (type help <topic>):
----------------------------------------
back   email  filepath  login  portfolio_delete    preferences          view
begin  exit   help      perms  portfolio_retrieve  resume_bullet_point
```

## Testing

To run all unit tests, simply enter `pytest`. To run a specific test file, enter `pytest tests/[test_file].py`


# Milestone 1 Documentation

## Team Contract

**Team 18**: Jimi Ademola, Priyansh Mathur, Tawana Ndlovu, Erem Ozdemir, Sam Sikora, Alex Taschuk

### Our Team's Vision and Goals

Going into this project, we wanted to make something that everyone in the team would be able to appreciate by the end of the year. We understood that to complete the app, we would need to work as a team that supported each other and communicated frequently. This meant leaving helpful comments on code reviews, ensuring that everyone knew what was expected of each other, and taking on as even a workload as possible.

### Expectations

#### Meetings

We all meet in person once a week to discuss our current individual in-progress tasks, what our personal goals and teams' goals are for the upcoming week(s), issues that are currently open, issues that may need to be created, and to brainstorm new features and ways that we can improve our app. During in-person meetings, we make sure that everyone is given equal opportunity to talk and/or ask any questions that they may have.

Everyone is expected to know ahead of time what they are currently working on, and, if they have any tasks for the upcoming week(s), what those tasks are. If someone needs guidance on what their next task should be, we talk as a team to figure out what they can do.

During these meetings, we will often use a whiteboard to take notes/visualize ideas, but one person in the team will take notes during the meeting if necessary.

#### Communication and Collaboration

##### Frequency of Communication

Everyone is expected to be regularly active in the group chat and participate in conversations about the project.

##### Communication Behavior

As a team, we give everyone equal opportunity to speak during in-person meetings. In-person and online, we treat each other with respect and provide constructive feedback, comments, and criticism when necessary. When we receive feedback on our work, we give genuine consideration to what our teammate has said.

##### Channels for Discussions

In addition to weekly in-person meetings, we frequently communicate in a group chat to discuss day-to-day items, let teammates know when they've been assigned a pull request (PR), and get input from each other on bug fixes and features in the process of being implemented.

##### Collaboration Process

Each member of the team is expected to put an equal amount of effort and work towards the project. We understand that individual workload outside of this course may vary from person to person throughout the semester, and that the complexity of tasks for the project will vary. Given this, it is expected that on a semester-long timeline, each member is contributing a "fair" amount to the project (i.e., they are not assigning themselves only easy tasks, or on the contrary, assigning themselves too many tasks, leaving very little for the others).

If at any point during the semester is there be a period of time (1-2 weeks) where a member is overloaded with work and will not have the bandwidth to contribute as much as the others, they should communicate this with the other members to ensure that the team's workload allocation takes this into consideration so as to minimize the amount of progress that is slowed down during that time.

PRs are expected to be thorough but concise. Before any PR is merged to a parent branch, two teammates are assigned to review the code and leave thoughts, comments, suggestions, etc., which may require the PR's author to fix some code in the PR. If this requires a larger team discussion, it should be set aside for the next in-person meeting, if necessary.

When a teammate is assigned to review a PR, it is expected that they will make an effort to properly review the code and thoroughly review it for any holes in the logic, bugs, etc.

Everyone is expected to review a similar number of PRs, and PR authors are expected to assign team members to their PRs evenly.

#### Distribution and Delivery of Work

##### Defining Project Tasks

Project tasks are defined in the GitHub [Issues](https://github.com/COSC-499-W2025/capstone-project-team-18/issues) tab of our repository. When an issue is made, it is expected that the title and description accurately represent the goal of the issue and comprehensively explain what the issue is, and any additional information that may be necessary, such as a proposed solution; it should provide enough context that any team member who may or may not be aware of the issue can understand it by reading its description.

Additionally, all of the `Assignees`, `Labels`, `Type`, `Projects`, `Relationships`, and any other relevant fields should be filled out.
- When the status of an issue changes (e.g., someone makes a PR for their issue), the issue's assignee should update the `Status` field (e.g., from `In Progress` to `In Review`).

##### Managing and Tracking Tasks

Along with the Issues tab, we also maintain team project board in our repository where we can easily view and sort issues according to attributes like their status, who is assigned to them, which dev area they are in, etc.

When a new task is created, either the author of the task assigns themselves to the task, or it is "up for grabs," meaning anyone may self-assign themselves to it.

##### Staying Aware of Others' Work and Avoiding Overlaps

As mentioned previously, our team frequently communicates, and everyone contributes evenly to work effort, features, and code reviews, which helps ensure that each member of the team stays in the loop about the work that others are doing and what the current state of the project is. Frequent communication also helps prevent the overlap, undoing, and/or redoing of someone else's work.

##### Accountability of task quality, quantity, and completion time

Because everyone is expected to put in an even amount of time and effort towards the project, it is expected that the quality of their work is also on par with everyone else's. While we do recognize that there are some differences in experience among our team, we do still have a standard of what is expected in code, such as well-written (i.e., efficient) code and concise documentation.

### Resolution Strategy

#### When an Issue Occurs for the First Time

##### Documenting the Issue

If there is an issue with a team member that has only occurred once, unless it is serious, we do not feel the need to document it. In the event of a serious issue, documentation will occur depending on what the problem is. If it happened in the team group chat, it will be screenshotted. Otherwise, a description of the issue will be written down. Any necessary information that gives context or is relevant to the problem will be included.

##### Who Will Document the Issue

All other team members will be present to ensure that the issue is accurately and fairly documented.

##### The Expected Change

We will discuss the issue with the member as a team, and what they can do moving forward to improve. This will include what we would like to see them change behavior-wise, and when we expect the change to occur.

#### When an Issue Repeatedly Occurs

##### Documenting the Repeated Issue

Again, documentation will occur depending on what the issue is. If it happened in the team group chat, it will be screenshotted. Otherwise, a description of the problem will be written down. Any necessary information that gives context or is relevant to the issue will be included. Additionally, we will document the previous conversation(s) that were had with the teammate, and what the outcome of the conversation(s) was.

##### Who Will Document The Repeated Issue

We will discuss the issue with the member as a team, and what they can do moving forward to improve. This will include what we would like to see them change behavior-wise, and when we expect the change to occur.

##### The Expected Change

We will discuss the issue with the member as a team, why the previous changes did not work, why the problem may be occurring repeatedly, and what we think they can do moving forward to improve. This includes what we would like to see them change behavior-wise, and when we expect the change to occur.

##### Executing the Firing Clause

If a repeated issue is severe enough, the rest of the team may discuss executing the firing clause. In order to fire a teammate, all other teammates must unanimously agree to the firing.


### Member Signatures (Printed)

**Jimi Ademola**:
- Jimi Ademola, 11-29-2025

**Priyansh Mathur**
- Priyansh Mathur, 11-29-2025

**Tawana Ndlovu**
- Tawana Ndlovu, 11-30-2025

**Erem Ozdemir**
- Erem Ozdemir, 11-30-2025

**Sam Sikora**
- Sam Sikora, 11-29-2025

**Alex Taschuk**
- Alex Taschuk, 11-29-2025


## Diagrams

### Data Flow Diagram - Level 0 & Level 1

![dfd lvl 0](/documentation/milestone-1/data-flow-diagrams/DFD-Level0.jpg)

![dfd lvl 1](/documentation/milestone-1/data-flow-diagrams/DFD-Level1.jpg)

### System Architecture

![system architecture](/documentation/milestone-1/system-architecture/system-architecture.jpeg)


## Requirements Checklist

- [x] Require the user to give consent for data access before proceeding
- [x] Parse a specified zipped folder containing nested folders and files
- [x] Return an error if the specified file is in the wrong format
- [x] Request user permission before using external services (e.g., LLM) and provide implications on data privacy about the user's data
- [x] Have alternative analyses in place if sending data to an external service is not permitted
- [x] Store user configurations for future use
- [x] Distinguish individual projects from collaborative projects
- [x] For a coding project, identify the programming language and framework used
- [x] Extrapolate individual contributions for a given collaboration project
- [x] Extract key contribution metrics in a project, displaying information about the duration of the project and activity type contribution frequency (e.g., code vs test vs design vs document), and other important information
- [x] Extract key skills from a given project
- [x] Output all the key information for a project
- [x] Store project information into a database
- [x] Retrieve previously generated portfolio information
- [x] Retrieve previously generated résumé item
- [x] Rank importance of each project based on user's contributions
- [x] Summarize the top ranked projects
- [x] Delete previously generated insights and ensure files that are shared across multiple reports do not get affected
- [x] Produce a chronological list of projects
- [x] Produce a chronological list of skills exercised
