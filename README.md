# CLI User Guide

## Quick Start
```bash
python3 src.app.py
```

## Commands
| Input | Action |
|-------|--------|
| `1` | Grant permissions |
| `2` | Set file path |
| `3` | Begin analysis |
| `4` | Email Configuration |
| `back`/`cancel` | Return to main menu |
| `exit` | Quit application |

## Workflow

### 1. Permissions
```
(PAF) 1
Do you consent to this program accessing files? (Y/N): Y
```
- `Y` = Grant access
- `N` = Exit app
- `back`/`cancel` = Main menu

### 2. File Path
```
(PAF) 2
Enter filepath: /path/to/project
```
- Enter any valid path
- `back`/`cancel` = Main menu

### 3. Begin
```
(PAF) 3
```
Requires steps `1` & `2` completed first; step `4` is optional.


### 4. Email Configuration
```
(PAF) 4
Enter email: jane@example.com
```
- Enter any valid path
- `back`/`cancel` = Main menu


## Example Session
```bash
(PAF) 1
(Y/N): Y
Thank you for consenting.

(PAF) 2
Enter filepath: ./myproject
Filepath successfully received

(PAF) 4
Enter email: john@example.com
Email successfully received

(PAF) 3
[Analysis begins...]
```

## Error Messages
- **"Missing consent"** → Complete step 1
- **"Invalid file"** → Check file path in step 2
- **"Invalid email"** → Check email in step 3
- **"Unknown command"** → Use 1, 2, 3, or help

## Testing
```bash
pytest tests/test_app_cli.py
```

## CLI Tool: Project Artifact Miner

We are building a command‑line interface (CLI) tool for mining project artifacts. The CLI entrypoint lives in `src/app.py` and uses Python's standard `cmd` module to provide an interactive prompt.

### How to run

Prerequisites: Python 3.11+ recommended.

1. Start Dev Container using devcontainer.json configuration
3. Start the CLI: `python src/app.py`

You should see the prompt `(PAF)` and a menu of options.

### Current features (implemented)

- Permissions flow: `perms` or `1`
  - Presents a consent statement and records consent (`Y/N`).
  - Exits if consent is not granted.
- Set filepath: `filepath` or `2`
  - Accepts a user‑provided path to the project (currently stored for later use).
- Begin mining: `begin` or `3`
  - Requires prior consent and a provided path.
  - Validates the provided path points to a readable file; mining logic is a placeholder for now.
- Back navigation: `back`
  - Returns to the previous screen based on simple command history tracking (last 3 commands are tracked).
- Menu/help
  - Numeric shortcuts `1/2/3` map to `perms/filepath/begin` respectively.
  - Built‑in `help`/`?` from `cmd` shows available commands.
- Exit: `exit`

### Under-the-hood components (work in progress)

The following modules scaffold the analysis/reporting pipeline and are partially implemented (see comments and `raise ValueError("Unimplemented")` markers):

- `src/classes/statistic.py`
  - Defines `Statistic`, `StatisticIndex`, and statistic templates for file/project/user levels (e.g., `LINES_IN_FILE`, `FILE_SIZE_BYTES`, dates, skills, etc.).
- `src/classes/report.py`
  - Base `Report` classes with `FileReport`, `ProjectReport`, `UserReport` placeholders.
- `src/classes/analyzer.py`
  - `BaseFileAnalyzer` and `TextFileAnalyzer` stubs that will collect file‑level statistics and produce `FileReport`s.

### Planned/next steps (from code comments)

- Implement mining logic inside `begin` to traverse the provided path and generate reports.
- Flesh out analyzers to compute basic file stats (size, created/modified dates, line counts, etc.).
- Implement `FileReport`, aggregate into `ProjectReport` and `UserReport` for project/user‑level insights.
- Improve path handling to support directories/projects (current `begin` validates a single file path).

### Notes

- Tests currently cover `StatisticIndex` behavior (`tests/test_stat_index.py`).
- The CLI uses a simple history mechanism to support `back`. This may evolve as the navigator grows.

****

# Milestone 1 Team Contract

**Team 18**: Jimi Ademola, Priyansh Mathur, Tawana Ndlovu, Erem Ozdemir, Sam Sikora, Alex Taschuk

## Our Team's Vision and Goals

Going into this project, we wanted to make something that everyone in the team would be able to appreciate by the end of the year. We understood that to complete the app, we would need to work as a team that supported each other and communicated frequently. This meant leaving helpful comments on code reviews, ensuring that everyone knew what was expected of each other, and taking on as even a workload as possible.

## Expectations

### Meetings

We all meet in person once a week to discuss our current individual in-progress tasks, what our personal goals and teams' goals are for the upcoming week(s), issues that are currently open, issues that may need to be created, and to brainstorm new features and ways that we can improve our app. During in-person meetings, we make sure that everyone is given equal opportunity to talk and/or ask any questions that they may have.

Everyone is expected to know ahead of time what they are currently working on, and, if they have any tasks for the upcoming week(s), what those tasks are. If someone needs guidance on what their next task should be, we talk as a team to figure out what they can do.

During these meetings, we will often use a whiteboard to take notes/visualize ideas, but one person in the team will take notes during the meeting if necessary.

### Communication and Collaboration

#### Frequency of Communication

In addition to weekly in-person meetings, we frequently communicate in a group chat to discuss day-to-day items, let teammates know when they've been assigned a pull request (PR), and get input from each other on bug fixes and features in the process of being implemented.

Everyone is expected to be regularly active in the group chat and participate in conversations about the project.

#### Communication Behavior

As a team, we give everyone equal opportunity to speak during in-person meetings. In-person and online, we treat each other with respect and provide constructive feedback, comments, and criticism when necessary. When we receive feedback on our work, we give genuine consideration to what our teammate has said.

#### Channels for discussions

Idk what she means by this

#### Collaboration Process

Each member of the team is expected to put an equal amount of effort and work towards the project.

PRs are expected to be thorough but concise. Before any PR is merged to a parent branch, two teammates are assigned to review the code and leave thoughts, comments, suggestions, etc., which may require the PR's author to fix some code in the PR. If this requires a larger team discussion, it should be set aside for the next in-person meeting, if necessary.

When a teammate is assigned to review a PR, it is expected that they will make an effort to properly review the code and thoroughly review it for any holes in the logic, bugs, etc.

Everyone is expected to review a similar number of PRs, and PR authors are expected to assign team members to their PRs evenly.

### Distribution and Delivery of Work

#### Defining Project Tasks

Project tasks are defined in the GitHub [Issues](https://github.com/COSC-499-W2025/capstone-project-team-18/issues) tab of our repository. When an issue is made, it is expected that the title and description accurately represent the goal of the issue and comprehensively explain what the issue is, and any additional information that may be necessary, such as a proposed solution; it should provide enough context that any team member who may or may not be aware of the issue can understand it by reading its description.

Additionally, all of the `Assignees`, `Labels`, `Type`, `Projects`, `Relationships`, and any other relevant fields should be filled out.
- When the status of an issue changes (e.g., someone makes a PR for their issue), the issue's assignee should update the `Status` field (e.g., from `In Progress` to `In Review`).

#### Managing and Tracking Tasks

Along with the Issues tab, we also maintain team project board in our repository where we can easily view and sort issues according to attributes like their status, who is assigned to them, which dev area they are in, etc.

When a new task is created, either the author of the task assigns themselves to the task, or it is "up for grabs," meaning anyone may self-assign themselves to it.

#### Staying Aware of Others' Work and Avoiding Overlaps

As mentioned previously, our team frequently communicates, and everyone contributes evenly to work effort, features, and code reviews, which helps ensure that each member of the team stays in the loop about the work that others are doing and what the current state of the project is. Frequent communication also helps prevent the overlap, undoing, and/or redoing of someone else's work.

#### Accountability of task quality, quantity, and completion time

Because everyone is expected to put in an even amount of time and effort towards the project, it is expected that the quality of their work is also on par with everyone else's. While we do recognize that there are some differences in experience among our team, we do still have a standard of what is expected in code, such as well-written (i.e., efficient) code and concise documentation.

## Resolution Strategy

### When an Issue Occurs for the First Time

#### Documenting the Issue

If there is an issue with a team member that has only occurred once, unless it is serious, we do not feel the need to document it. In the event of a serious issue, documentation will occur depending on what the problem is. If it happened in the team group chat, it will be screenshotted. Otherwise, a description of the issue will be written down. Any necessary information that gives context or is relevant to the problem will be included.

#### Who Will Document the Issue

All other team members will be present to ensure that the issue is accurately and fairly documented.

#### The Expected Change

We will discuss the issue with the member as a team, and what they can do moving forward to improve. This will include what we would like to see them change behavior-wise, and when we expect the change to occur.

### When an Issue Repeatedly Occurs

#### Documenting the Repeated Issue

Again, documentation will occur depending on what the issue is. If it happened in the team group chat, it will be screenshotted. Otherwise, a description of the problem will be written down. Any necessary information that gives context or is relevant to the issue will be included. Additionally, we will document the previous conversation(s) that were had with the teammate, and what the outcome of the conversation(s) was.

#### Who Will Document The Repeated Issue

We will discuss the issue with the member as a team, and what they can do moving forward to improve. This will include what we would like to see them change behavior-wise, and when we expect the change to occur.

#### The Expected Change

We will discuss the issue with the member as a team, why the previous changes did not work, why the problem may be occurring repeatedly, and what we think they can do moving forward to improve. This includes what we would like to see them change behavior-wise, and when we expect the change to occur.

#### Executing the Firing Clause

If a repeated issue is severe enough, the rest of the team may discuss executing the firing clause. In order to fire a teammate, all other teammates must unanimously agree to the firing.


## Member Signatures (Printed)

**Jimi Ademola**:

**Priyansh Mathur**

**Tawana Ndlovu**

**Erem Ozdemir**

**Sam Sikora**

**Alex Taschuk**
- Alex Taschuk, 11-29-2025
