# Priyansh Mathur Personal Logs Term 2

## Table of Contents

**[Week 1, Jan. 05-11](#week-1-jan-05-11)**

**[Week 2, Jan. 12-18](#week-2-jan-12-18)**

**[Week 3, Jan. 19-25](#week-3-jan-19-25)**

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
