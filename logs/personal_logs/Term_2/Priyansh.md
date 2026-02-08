# Priyansh Mathur Personal Logs Term 2

## Table of Contents

**[Week 1, Jan. 05-11](#week-1-jan-05-11)**

**[Week 2, Jan. 12-18](#week-2-jan-12-18)**

**[Week 3, Jan. 19-25](#week-3-jan-19-25)**

**[Week 4-5, Jan. 26-Feb. 08](#week-4-5-jan-26-feb-08)**

---

## Week 1, Jan. 05-11

### Peer Eval
![Peer Eval](../../../logs/log_images/personal_log_imgs/Term_2/priyansh/priyansh_week1_log.png)

### Recap
This week, our team reconvened after the break to reassess where we stood with Milestone 1. We discussed our individual progress, highlighted areas that needed improvement, and confirmed the remaining tasks required to complete the milestone. We have also started planning and discussing Milestone 2 requirments. Additionally I reviewed PR #341 Tawana Term 2 Week 1 Personal Log and PR #322 Refactor Test Directory by Sam

## Week 2, Jan. 12-18

### Peer Eval
![Peer Eval](../../../logs/log_images/personal_log_imgs/Term_2/priyansh/priyansh_week2_term2_log.png)

### Recap

Building on the planning and coordination from Week 1, this week focused on divison of teams to handle tasks for Milestone 2.

#### Coding Tasks

I completed [PR #364 - Extract README Key Phrases to Auto‑Tag Projects](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/364), which closes [Issue #359](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/359). This PR implements sophisticated README analysis using three ML models:

- **KeyBERT** for extracting key phrases and technical tags from README content
- **BERTopic** for discovering project themes through topic modeling across multiple README files
- **BART-MNLI** for zero-shot tone classification (technical, casual, educational, promotional)

The implementation aggregates README insights at the project level and surfaces them in portfolio output. I created comprehensive docstrings for all functions, implemented error handling for BERTopic edge cases (e.g., zero-size arrays when insufficient documents exist)

#### Reviewing Tasks

I reviewed two critical PRs this week:

1. [PR #356 - Implement DB Migration & Version Control via Alembic](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/356) by Alex


2. [PR #358 - Fix Contribution Percentage Bug](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/358) by Sam


#### Goals for Next Week
- Continue work on Milestone 2 features, involving additional ML support and analysis
- Support the team with any Milestone 1 deliverables and documentation

## Week 3, Jan. 19-25

### Peer Eval
![Peer Eval](../../../logs/log_images/personal_log_imgs/Term_2/priyansh/priyansh_week3_term2_log.png)

### Recap
This Week the team focused on buliding a base template for the frontend UI, creating meaningful API which will service the backend to the frontend, improved ML analysis on README files and contribution analysis on ProjectReport, and Alembic DB related fixes.

#### Coding Tasks
I completed [PR #380 - Improve README insights stability and CLI output formatting and adding docstrings](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/380), which closes [Issue #379](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/379).

This PR adds a safer README insights flow so themes/tone don’t disappear when BERTopic fails, filters URL/noise terms, and trims long tag/theme lists for readability. It also silences ML/log spam in the CLI and clears old logs on startup. This fixes the issue where some projects showed no themes/tone and where CLI output was overly noisy.

#### Reviewing Tasks
1. [PR #377 - Alembic hotfix, created initial revision file for the database](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/377) by Alex

2. [PR #381 - ML-based contribution pattern analysis for commit classification, work patterns, and collaboration roles ](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/381) by Erem

My feedback focused on code correctness, test coverage, and edge case handling.

#### Goals for Next Week
- Understanding how ML Analysis can be further implemented in our system
- Buliding Frontend UI

## Week 4-5, Jan. 26-Feb. 08

### Peer Eval
*Peer evaluation screenshots to be added*

### Recap
These two weeks were focused on enhancing ML-based analysis capabilities, particularly improving README theme extraction and implementing comprehensive project summary generation for portfolio output. The team also made significant progress on frontend UI development with Electron, API endpoints, and system optimization.

#### Coding Tasks

**1. [PR #401 - Improve README Theme Extraction](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/401)** (Merged)

This PR closes [Issue #399](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/399) and significantly improves the quality of theme extraction from project README files. Key improvements include:

- **Enhanced filtering**: Added programming languages to the filter list to prevent generic terms from appearing as themes
- **Acronym support**: Modified filtering logic to allow short acronym themes (e.g., "ML", "API", "CI/CD") while still filtering out noise
- **Better theme detection**: Improved the algorithm to identify more meaningful and relevant project themes
- **Documentation**: Added inline comments explaining the changes and rationale

The improvements result in cleaner, more meaningful theme tags for projects in portfolio output.

**2. [PR #414 - Display Textual Information About a Project](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/414)** (In Progress)

This PR closes [Issue #406](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/406) and introduces a general-purpose project summary feature that adds concise, professional 2–3 sentence descriptions to each portfolio project. The summaries cover project goals, technologies used, and the user's contribution. Key implementation details:

- **ML-based generation**: Implemented ML-generated project summaries using existing project facts (themes/tags, frameworks/languages, and contribution metrics)
- **Deterministic fallback**: Designed a robust fallback system to ensure consistent output quality when ML generation is unavailable
- **Text processing**: Implemented regex-based sentence splitting for more accurate text parsing
- **Contribution normalization**: Normalized percentage contribution statistics for accurate representation
- **Import safety**: Added lazy-loading for ML dependencies to prevent import-time crashes in minimal CI/dev environments
- **Comprehensive documentation**: Added detailed inline comments and documentation for all functions

The feature received approvals from Alex and Tawana, with feedback from Erem being addressed regarding anchor normalization and contribution checks.

**3. [PR #411 - ML Analysis for User Summary](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/411)** (In Progress)

This ongoing PR closes [Issue #402](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/402) and implements ML-generated user summaries for portfolio output. The main goal is producing professional, personalized summaries instead of generic or repetitive text, with language that adapts to each user's profile (focus, role, work style, and experience stage). Major contributions include:

- **Project summaries**: Implemented per-project summary generation that analyzes contribution patterns, project characteristics, and technical contributions
- **Resume summary enhancement**: Improved the overall resume summary to better highlight user skills, project diversity, and work patterns
- **Contribution normalization**: Normalized percentage contribution statistics across projects for accurate representation
- **Text processing improvements**:
  - Implemented regex-based sentence splitting for more robust text parsing
  - Adjusted project tone metrics for better classification
  - Combined and optimized keyword mappings for domain detection
- **Code organization**: Moved tests to the ML folder for better structure and added comprehensive documentation for all functions
- **Addressed peer feedback**: Incorporated review comments from Sam and Jimi regarding model warm-up placement, code readability, and preventing bloated functions

The implementation uses multiple layers of ML analysis to generate meaningful summaries that capture the essence of user contributions across projects. Currently undergoing review with requested changes being addressed.

#### Reviewing Tasks

During these weeks, I reviewed the following PRs to support team progress on Milestone 2:

1. [PR #383 - Portfolio Resume Generation Services](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/383) by Sam
2. [PR #388 - Electron UI Init](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/388) by Jimi & Team
3. [PR #391 - Uncontributed Files](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/391) by Jimi
4. [PR #395 - Contribution Hotfix](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/395) by Sam
5. [PR #397 - Optimize Tests](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/397) by Sam
6. [PR #408 - Alembic Revision Hotfix](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/408) by Alex
7. [PR #409 - Implement Endpoints Get Projects](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/409) by Erem

My reviews focused on ensuring code quality, proper error handling, test coverage, and alignment with our system architecture.

#### Goals for Next Week
- Complete PR #414 and PR #411, addressing remaining review comments
- Continue supporting frontend integration efforts
- Work on remaining Milestone 2 deliverables and documentation

