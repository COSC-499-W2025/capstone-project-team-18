# Tawana Ndlovu Personal Logs Term 2

## Table of Contents

**[Week 1, 01/05 - 01/11](#week-1-0105---0111)**

**[Week 2, 01/12 - 01/18](#week-2-0112---0118)**

**[Week 3, 01/19 - 01/25](#week-3-0119---0125)**

---

# Week 3 01/19 - 01/25
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week3_log.png)

This week, I focused on initializing the Electron-based UI and setting up a clean integration between the frontend and our existing FastAPI backend. I created an Electron + React + Vite scaffold under the ui/ directory and implemented a centralized API client to handle all frontend communication with FastAPI.

To validate the setup, I added a simple landing page that displays the active API base URL, shows backend connectivity status (Connected / Disconnected), and allows querying the /projects and /skills endpoints, displaying responses as formatted JSON. I also added lightweight unit tests for the API client using Vitest to verify URL handling and error cases without requiring the backend to be running.

This work establishes a solid foundation for future UI development in Milestone 3.

Additionally, I reviewed the following PRs:
1. [PR `#378` Robust start_miner_service](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/378)
2. [PR `#374` Move src/infrastructure/database to src/database](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/374)


# Week 2 01/12 - 01/18

# Peer Evaluation!
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week2_log.png)

# Recap on your week goals
This week, I focused on improving the organization and maintainability of our project logs by refactoring the logs/ directory into a clear, term-based structure. Logs are now grouped by Term 1 and Term 2, with separate folders for personal logs, team logs, and their associated images, making navigation and long-term maintenance easier.

As part of this refactor, I updated all affected Markdown files to ensure paths, image references, and Tables of Contents were correct, and manually verified that all internal links resolve properly in GitHub preview. These changes were strictly structural and did not alter any log content.

Additionally, I reviewed the following PRs:
1. [PR `#358` Fix Contribution Percentage Bug](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/358)
2. [PR `#368` Additional Git Preferences](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/368)
3. [PR `#333` Log Everything](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/333)
 
# Week 1 01/05 - 01/11

# Peer Evaluation!
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week1_log.png)

# Recap on your week goals
This week, our team met to regroup after the break and review the current state of Milestone 1. We walked through our progress together, identified gaps, and aligned on what still needed refinement. We also spoke directly with the TA to fine-tune Milestone 1 requirements, clarify expectations, and ensure our deliverables were aligned with the rubric.

In addition to team coordination, I reviewed Sam’s PR `#332` (Refactor Test Directory). The changes significantly improved the organization, isolation, and maintainability of our test suite. 

Overall, this week was centered on alignment, clarification, and quality assurance as we finalized Milestone 1 and prepared for the next phase of development.