# Team 18 — Week 10, Nov. 3–9

## Overview

### Milestone Goals

Based on issues created and actively worked on during Week 10 (Nov 3-9):

- **Cross-platform archive extraction support** (.zip, .tar.gz, .gz, .7z)
  - [Issue #59](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/59) - Add functionality for zipped files
  - [Issue #125](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/125) - Determine system's OS to use corresponding unzip command
  - [Issue #171](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/171) - Update CLI to extract archive files before analysis ✓
  - [Issue #173](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/173) - Improve file path handling for cross-platform compatibility

- **Language identification functionality**
  - [Issue #156](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/156) - Identify languages used

- **Database management and refactoring**
  - [Issue #153](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/153) - Move database directory into src directory ✓
  - [Issue #76](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/76) - User Authentication for Database ✓
  - [Issue #148](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/148) - Write reports to DB
  - [Issue #147](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/147) - Update existing database columns at runtime

- **Resume/Portfolio generation** (Milestone 1 key requirements)
  - [Issue #127](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/127) - Create Class Structure for a Resume ✓
  - [Issue #161](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/161) - Create design structure for portfolio
  - [Issue #164](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/164) - Produce chronological list of projects
  - [Issue #165](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/165) - Produce chronological list of skills
  - [Issue #137](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/137) - Include the list of Skills in the Generated Resume

- **Git contribution analysis improvements**
  - [Issue #78](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/78) - Extrapolate individual contributions for group projects
  - [Issue #163](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/163) - Refactor Git analyze function
  - [Issue #176](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/176) - Improve git contribution statistics

- **Project analysis enhancements**
  - [Issue #104](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/104) - Make discover_projects Function Return Project Path and Support Project Heuristics ✓
  - [Issue #157](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/157) - Rank Projects Against Each Other

- **User preferences and permissions**
  - [Issue #152](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/152) - Ask User Consent for Connecting to their Git
  - [Issue #158](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/158) - Store user preferences as JSON

- **Testing and code organization**
  - [Issue #160](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/160) - Refactor tests directory
  - [Issue #162](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/162) - Organize our tests into sub-directories within tests
  - [Issue #166](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/166) - Create some global_fixtures.py class where all of the fixtures that multiple tests will use

✓ = Completed during Week 10

### Burnup Chart

![Image of burnup chart for this week](../log_images/team_log_imgs/burnup_week10.png)

## Details

### Username Mapping

```
jademola -> Jimi Ademola
eremozdemir -> Erem Ozdemir
thndlovu -> Tawana Ndlovu
alextaschuk -> Alex Taschuk
sjsikora -> Sam Sikora
priyansh1913 -> Priyansh Mathur
```

### Completed Tasks

**Key Feature PRs Merged:**

- **PR #170** (Issue #125): **Priyansh Mathur** - Implemented robust OS detection logic to determine the host operating system in both dev containers and end-user environments, enabling correct extraction commands for Windows, macOS, and Linux. Added comprehensive OS detection tests.

- **PR #169** (Issue #59): **Priyansh Mathur** - Added support for extracting .zip, .tar.gz, .gz, and 7z files with OS-aware extraction logic. Implemented system tool usage with Python library fallbacks for reliability across all platforms. Added py7zr to requirements and comprehensive extraction tests for all formats.

- **PR #168** (Issue #156): **Sam Sikora** - Implemented language identification functionality to detect and catalog programming languages used in analyzed projects.

- **PR #154** (Issue #153): **Alex Taschuk** - Moved the entire `database` directory into `src` and updated all related imports, improving code organization and project structure.

**Closed Issues:**

![Closed Issue 1](../log_images/team_log_imgs/close_issue1.png)
![Closed Issue 2](../log_images/team_log_imgs/close_issue2.png)
![Closed Issue 3](../log_images/team_log_imgs/close_issue3.png)
![Closed Issue 4](../log_images/team_log_imgs/close_issue4.png)
![Closed Issue 5](../log_images/team_log_imgs/close_issue5.png)


### In Progress Tasks

**Open PRs (under review):**

- **PR #181** (Issue #158): **Erem Ozdemir** - Core JSON Preferences Foundation - Implemented UserPreferences class with JSON storage capabilities and CLI integration for automatic save/restore of user data between sessions
- **PR #179** (Issue #164): **Tawana Ndlovu** - Chronological project list implementation
- **PR #178** (Issue #176): **Jimi Ademola** - Expanding Git-style group contribution statistics
- **PR #175** (Issue #163): **Jimi Ademola** - Refactoring Git analyze function
- **PR #172**: **Jimi Ademola** - Removed redundant print statements in test code
- **PR #167** (Issue #111): **Alex Taschuk** - Database documentation and improvements
- **PR #155**: **Sam Sikora** - Altered behavior of start date collection and fixed date collection issue

### Test Report

All 158 tests passing on the develop branch as of the latest merge, demonstrating robust code quality and comprehensive test coverage across all features.

![Test Report](../log_images/team_log_imgs/tests_week10.png)



