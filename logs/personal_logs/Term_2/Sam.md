# Sam Sikora Personal Logs Term 2

## **[This Week](#week-2-0112---0118)**

## Table of Contents

- **[Week 2, 01/12 - 01/18](#week-2-0112---0118)**
- **[Week 1, 01/05 - 01/11](#week-1-0105---0111--winter-break)**

---

## Week 3 01/19-01/25

![Peer Eval SS](../../../logs/log_images/personal_log_imgs/Term_2/sam/sam_week3_log.png)

### Coding Tasks

This week my PR's focused adding robustness to our system for the upcoming API. This included making sure that the start_miner function could handle project level errors instead of just erroring out, making sure that the miner would only mine to the project level, and simplifying the passing of data in our code (PR #378). Also, I created a entire new class system to handle portfolios. This ensure that we have a system to update, incrementaly add, and resolve conflicts with our portfilo objects.

- [PR #378 Robust start_miner_service](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/378)
- [PR #383 Portfolio Class Sytem](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/383)

### Testing Tasks

I added tests for each of my PRs and apated existing tests to deal with the movement of logic.

### Review Tasks

I reviewed the following PRs
- [PR #381 ML-based contribution pattern analysis for commit classification, work patterns, and collaboration roles](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/381)
- [PR #377 Alembic hotfix, created initial revision file for the database](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/377)

### Summary

This week focused on big sweeping architecure additions and changes. However, with this new changes, it should be really easy to create endpoints for our API. Next week will focus on getting endpoints developed.

## Week 2 01/12 - 01/18

![Peer Eval SS](../../../logs/log_images/personal_log_imgs/Term_2/sam/sam_week2_log.png)

### Coding Tasks

This week my PR's from winter break that I mentioned last week were all reviewed and merged. See last week's log for details, but this includes:
- [PR #329 Logic for Serializing and Deserializing Statistic Values](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/329)
- [PR #330 Capsulate Project and User Report Statistic Logic Analysis](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/330)
- [PR #332 Refactor Test Directory](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/332)
- [PR #333 Log Everything](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/333)

Additionaly, I also adapted the logic of the project upload or start_miner function so that it was decoupled from the CLI, and thus could be run stateless from by an API in the future. ([#351](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/351)).

I also configured and initialized the FastAPI service. This also included writing placeholder functions for all the endpoints required by Milestone #2 ([#355](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/355)).

### Testing Tasks

I added tests to the API PR to make sure all Milestone #2 required endpoints existed and ran properly, and a very simple API ping to verify the service was running.

For the decoupling, I had to write some new unzip util functions so I added tests for all the new helper functions I wrote ([#351](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/351)).

I also commited tests onto Jimi's bug fix PR to make sure that it we had a test for this bug and it doesn't happen again ([#358](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/358)).

### Review Tasks

I reviewed Alex's PR [#356](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/356) and Priyansh's PR [#364](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/364)

### Summary

Last week was about getting huge refactors in to give us a clean slate. Now I am focusing on thinking about the big architercure changes that will allow us to best deliever on Milestone #2. I am the lead of the API team, so I will be focused on getting some endpoints delivered.



## Week 1 01/05 - 01/11 + Winter Break

![Peer Eval SS](../../../logs/log_images/personal_log_imgs/Term_2/sam/sam_week1_log.png)

I worked mainly on refactoring our code. I mostly focused on making and implementing consistent conventions and taking god classes and spliting the responsiblities into many different, refactorable code pieces. Specially, I split our report and analyzer code pieces into different files (#321), I added an empty file check before we analyzed files (#327), I created a one size fits all serializer and deserializer for the database (#329), I adapted the way we calcuated statistics to prevent shotgun changes when adding new statistics (#330), refactor the entire tests folder to split the tests up into logical subfolders and making sure the tests use the same, consistent helper functions (#332), and lastly I added support for logging through the system and added log messages (#333).
