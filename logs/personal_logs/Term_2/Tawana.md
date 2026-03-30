# Tawana Ndlovu Personal Logs Term 2

## Table of Contents

**[Week 1, 01/05 - 01/11](#week-1-0105---0111)**

**[Week 2, 01/12 - 01/18](#week-2-0112---0118)**

**[Week 3, 01/19 - 01/25](#week-3-0119---0125)**

**[Week 4–5, 01/26 - 02/08](#week-4-5-0126---0208)**

**[Week 8, 02/23 - 03/01](#week-8-0223---0301)**

**[Week 9, 03/02 - 03/08](#week-9-0302---0308)**

**[Week 10, 03/09 - 03/15](#week-10-0309---0315)**

**[Week 12, 03/23 - 03/29](#week-12-0323---0329)**

---

# Week 12 03/23 - 03/29
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week12_log.png)
This week, I focused on expanding the resume system into a more complete and customizable workflow, aligning it closely with the portfolio-style experience across the application. A major part of this work involved introducing multi-resume management, allowing users to view, navigate, and edit multiple generated resumes through a dedicated collection page. I implemented a new resume collection endpoint, built out the ResumesPage, and updated routing and navigation to follow a consistent collection/detail pattern similar to portfolios. I also cleaned up the ResumePage to be editor-only and removed the legacy generation flow. [PR `534` Resume Frontend Suite](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/534)

In parallel, I enhanced resume customization by restructuring education and awards into structured objects across the full stack, including backend schema updates, normalization for legacy data, and redesigned frontend editing components. I improved export functionality by refining the LaTeX renderer and adding Word (.docx) export support, along with better formatting for links and layout consistency. Additionally, I introduced profile-based defaults for resume names, fixed a persistence issue with user-edited skills, and implemented a non-blocking warning system to notify users when their resume exceeds a single page. [PR `#563` Resume Frontend Suite 2.0](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/563)

On the UI side, I enhanced the project upload experience by implementing a loading skeleton and improved feedback during project analysis. This included adding a polling mechanism to detect when analysis completes, refining rendering logic for different states, and improving the transition from upload to dashboard. Overall, these changes make the system more responsive, intuitive, and aligned with a production-ready workflow. [PR `#523` Electron Skeleton UI & Loading Loop](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/523)

Additionally, I worked on refining the overall frontend UI/UX to improve consistency and usability across the dashboard, projects, and resume flows. This included redesigning the dashboard layout for better information hierarchy, aligning project and resume cards visually, and cleaning up project detail pages by removing unused or misleading elements. I also improved feedback mechanisms in the resume editing experience and standardized styling across components, ensuring the UI more accurately reflects backend data and provides a cleaner, more intuitive user experience. [PR `502` Peer testing Endpoint Connection](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/502)

Additionally, I reviewed the following PRs:
1. [PR `#564` Removed Extra Skills Levels](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/564)
2. [PR `#557` Small changes to Profile page](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/557)
3. [PR `526` GitHub pages deployment](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/526)
4. [PR `517` User GitHub OAuth Flow](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/517)
5. [PR `494` 494 add more project insights](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/518)

# Week 10 03/09 - 03/15
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week10_log.png)

This week, I began development of the Electron UI required for peer testing. The focus was on implementing the core user flows needed to interact with the backend system, including editing user settings and consent, uploading projects, viewing project details, and generating a resume view.

I started by restructuring the current home page into a dashboard that displays projects and provides quick actions such as Start Mining and Settings. I also implemented a settings modal connected to the Get UserConfig and Edit UserConfig endpoints, allowing users to modify their configuration and consent preferences directly from the UI.

Additionally, I worked on the project upload flow by connecting a modal to the miner endpoint and adding validation to prevent submissions when user consent is not provided. I also began implementing the project details and resume views, which retrieve project data and allow basic editing of generated resume content.

Additionally, I reviewed the following PRs:
1. [PR `#485` Get GROUP BASED statistics](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/485)
2. [PR `#469` Upload Project Thumbnail Endpoint](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/469)

# Week 9 03/02 - 03/08
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week9_log.png)

This week, I implemented backend support for user-controlled information representation across portfolio projects, allowing users to customize how mined project data is presented. I extended the ProjectReportModel schema to support overrides such as project ranking, chronology corrections, highlighted skills, showcase selection, and customizable showcase metadata. I also introduced endpoints to persist these preferences and refactored showcase formatting into a shared helper to remove duplicated logic, with additional validation to prevent invalid states (e.g., negative ranking values). This work was completed in:
[PR `#461` User Information Representation (Personalization)](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/461).

I also implemented a small backend and UI hotfix to restore expected endpoint behaviour and frontend rendering. This included fixing router registrations in api.py, correcting response handling in the privacy consent endpoint, and resolving a Skills page rendering issue. This work was completed in: [PR `#460` Endpoints HotFix](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/460).

Additionally, I reviewed the following PRs:
1. [PR `#463` 462 job readiness analysis feature](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/463)

# Week 8 02/23 - 03/01
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week8_log.png)

This week, I focused on extending the FastAPI backend to support rendering project data as structured resume and portfolio entries. I implemented new endpoints to expose presentation-ready project information derived from the existing ProjectReport model, including proper date normalization and strongly typed response schemas.

I introduced the GET /projects/{project_name}/showcase endpoint to generate portfolio-style project representations and the GET /projects/{project_name}/resume-item endpoint to generate resume-formatted entries. Both endpoints include unit tests covering 200, 404, and 500 behaviors, with mocked CRUD layers to isolate endpoint logic from database state. This work was completed in:
[PR `#441` Display Textual Information About A Project As A Portfolio Showcase](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/441) and [PR `#444` Display Textual Information About A Project As A Resume Item](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/444)

I then extended this functionality to allow users to customize and persist showcase content through new override endpoints under /projects/{project_name}/showcase/customization. This included schema extensions, override merge logic, framework filtering, and FastAPI lifespan integration for automatic schema initialization. Unit tests were added to validate persistence and merge behavior. This was implemented in:
[PR `#451` Customize And Save Information About A Portfolio Showcase Project](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/451).

These updates establish backend support for structured, editable portfolio and resume presentation features, with frontend integration planned next.
Additionally, I reviewed the following PRs:
1. [PR `#438` Fix FILE_HASH merge conflicts](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/438)
2. [PR `#446` Allow report updates](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/446)

# Week 4-5 01/26 - 02/08
[Peer Eval THN](../../../logs/log_images/personal_log_imgs/Term_2/tawana/tawana_week4-5_log.png)

Over Weeks 4–5, I expanded the Electron-based UI beyond the initial scaffold by implementing basic frontend pages for browsing projects and skills and wiring them to the existing FastAPI endpoints. I added client-side routing for project lists and project detail views, with appropriate loading, empty-state, and error handling aligned with the current backend contracts.

I also extended the centralized API client to support fetching individual projects and updated the backend connectivity check to use the lightweight /ping endpoint, decoupling UI checks from database-backed routes. Alongside this, I expanded Vitest unit test coverage for the API client to validate URL construction, parameter encoding, and error handling without requiring the backend to be running. This was done in the following PR: [PR `#425` Add basic Electron UI with projects and skills Pages](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/425)

In addition, I refined the original Electron UI initialization work by incorporating feedback, configuring CORS for local development, adding a ui/README.md to document frontend setup and testing, and adding UI tests to GitHub Actions workflows. This was done in the following PR: [PR `#388` Initialize Electron UI and FastAPI Integration](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/388)

Additionally, I reviewed the following PRs:
1. [PR `#417` LaTeX to PDF Rendering](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/417)
2. [PR `#419` [perf] Speed-up file reports analysis](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/419)
3. [PR `#414` 406 display textual information about a project](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/414)
4. [PR `#395` Contribution Metric HOTFIX](https://github.com/COSC-499-W2025/capstone-project-team-18/pull/395)

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