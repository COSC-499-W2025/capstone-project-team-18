# Jimi Ademola Personal Logs Term 2

## Table of Contents

**[Week 1, Jan. 05 - 11](#week-1-jan-05---11)**
**[Week 2, Jan. 12 - 18](#week-1-jan-12---18)**
**[Week 3, Jan. 19 - 25](#week-1-jan-19---25)**

---

## Week 1, Jan. 05 - 11

### Peer Eval

![Peer Eval SS](../../../logs/log_images/personal_log_imgs/Term_2/jimi/jimi_week1_log.png)


### Recap

This week we met as a group to discuss all Milestone 1 requirements and ensure they were correctly met. Additionally I reviewed multiple PRs, including [#321](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/321) and [#327](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/327) which were refactoring changes made to simplify the project for future changes.

## Week 2, Jan. 12 - 18

### Peer Eval

![Peer Eval SS](../../../logs/log_images/personal_log_imgs/Term_2/jimi/jimi_week2_log.png)


### Recap

Last week we met as a group to prepare for Milestone 2 and figure out which requirements were currently missing.

### This Week

This week we first met to create varying teams such as ML, system analysis, database & frontend. With each person leading a single group and also being a part of many, there was proper division of the work. No major issues in terms of development or progress were encountered this week.

### Coding Tasks

I focused on reoslving some bugs that had been found in the code. This included finally fixing the contribution percentage error, which was caused by line counts being tracked in junk files and can be found in [#358](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/358).
The second bug fix was an error thrown in the CLI due to the logging files. This was resolved and a `constants.py` file was created for future reference. This is found at [#357](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/357)
Lastly, I added a secondary check for all contribution and commit-style metrics using a GitHub account check. This adds all back-end logic and additionally updates the information displayed in the _LaTeX_ resume. Found in [#368](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/368).

### Testing Tasks

Tests were added and debugged primarly for the last feature in PR **#368**. This was as multiple tests had to be reconfigured to have an additional parameter, while new tests additionally had to be created to ensure functionality. Functional tests were added to ensure the total contribution bug in Issue [#296](https://github.com/COSC-499-W2025/capstone-project-team-18/issues/296) did not reoccur pending changes. Beyond that, tests were done and reviewed for the alembic database changes.

### Reviewing Tasks

I reviewed [#351](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/351) which was changes needed to move away from a CLI interface towards a full frontend and such also included API services placeholders. I additionally reviewed [#356](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/356) which was the Alembic database functionality which addeed migration features / version control to the DB. This then inspired the need for `constants.py` to avoid hard-coded file paths.

### Next Week

Next week will bring the first stages of the frontend and 'inference' from the newly computed insights in the ML models. Additionally, we will need to integrate the API to tie togther the current analysis with the ability for the user to fetch information whether through a direct API call or a User Interface.

## Week 3, Jan. 19 - 25

### Peer Eval

![Peer Eval SS](../../../logs/log_images/personal_log_imgs/Term_2/jimi/jimi_week2_log.png)


### Recap

Last week we worked on the frontend connection which included API integration, a new Portfolio class system, API integration and improvements on service includes ML analysis and other key requirements.

### This Week

This week we first met to create varying teams such as ML, system analysis, database & frontend. With each person leading a single group and also being a part of many, there was proper division of the work. No major issues in terms of development or progress were encountered this week.

### Coding Tasks

I focused on resolving some fixes and adding smoe key requirements. This included adjusting the behaviour for files which are not contributed to and can be found in [#391](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/391).
The second feature was a key requirement to recognize and not reaanalyze duplicate files. This was resolved using a `MD5` hash value and a database check. This is found at [#393](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/393)

### Testing Tasks

Tests were added and debugged primarly for the last feature in PR **#393**. This was as multiple tests had to be added to ensure correct access to the database, proper table creation with the additnoal row and ensure duplicates were checked across many edge cases (uncontributed files etc...).  Beyond that, tests were done and reviewed for the `INFO_FILES` change in **#391**, which simply checked that fileReports were being generated correctly and prior functionality was unaffected.

### Reviewing Tasks

I reviewed [#380](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/388) which was changes needed improve on the ML insights on project tone and themes done by Priyansh. I additionally reviewed [#388](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/356) which was the initializatino of the Electron-based UI and integration with the current FastAPI setup.


### Next Week
Next week will further connect the frontend and backend by allowing for near-complete integration utlizing API calls. Additonally, the UI will be customized to further include more customization and the varying required pages.

