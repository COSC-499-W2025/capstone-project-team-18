# Week 14 12/01 - 12/07

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week14_log.png)

# Recap on your week goals
This week, I focused primarily on reviewing team PRs and supporting the completion of Milestone 1. I reviewed Sam’s `#273` (reworked resume class structure and LaTeX export), `#300` (updated resume printing using the new builder), and `#311` (hot fix for naming reports). I also reviewed Alex’s `#285` (Milestone 1 README updates) and Priyansh’s `#306` (fix for duplicate portfolio title renaming). My feedback ensured clarity, correct integration with existing logic, and that tests and documentation were consistent.

In addition to code reviews, I helped create and polish our Milestone 1 presentation, focusing on organization, flow, and readability. I also participated in delivering the presentation in class and reviewing other teams’ presentations as part of the milestone evaluations.

Overall, this week centered on quality assurance, presentation work, and strengthening team coordination as we wrapped up Milestone 1.

# Week 13 11/24 - 11/30

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week13_log.png)

# Recap on your week goals
This week, I completed Issue `#253` by adding the new CLI feature (10) Get resume bullet point, which retrieves resume-ready bullet points for any previously stored ProjectReport. The feature integrates with get_project_from_project_name() and uses bullet_point_builder() to generate bullets based on project stats, with full handling for exit, back/cancel, empty input, and missing project names. I also updated the CLI menu and routing, and added tests to test_app_cli.py to validate all input paths and successful bullet generation. All tests pass.

I also reviewed team PRs, including Jimi’s `#270` (Ctrl+C handling), Alex’s `#268` (Milestone 1 Team Contract), Sam’s `#263` (ProjectReport refactor), and Sam’s `#257` (weighted skills logic).

# Week 12 11/17 - 11/23

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week12_log.png)

# Recap on your week goals
This week, I completed Issue `#165` by implementing UserReport.get_chronological_skills(), which generates a time-ordered list of skills based on the earliest project in which each skill appears. The method supports newest-first sorting, handles undated skills, and returns either a formatted string or list. A full test suite (test_user_report_chronological_skills.py) validates ordering, formatting, and edge-case behavior.

Additionally, I reviewed multiple PRs this week to support team progress. I reviewed Priyansh’s PR `#231` on implementing project ranking and Jimi’s PR `#230` on improving git contribution accuracy, providing feedback on correctness, clarity, and test coverage.

# Week 10 11/03 - 11/09

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week10_log.png)

# Recap on your week goals
This week, my focus was completing Issue `#164`, which implements the “Produce a chronological list of projects” requirement from Milestone #1. I added UserReport.get_chronological_projects(), which formats and outputs projects ordered by start date, includes start/end dates, and automatically numbers entries. A full test suite (tests/test_user_report_projects.py) was added to validate correctness, sorting behavior, formatting, and edge cases (e.g., missing dates).

Additionally, I reviewed multiple PRs this week to support team progress. I reviewed Reviewed Alex’s PR `#159` - database documentation + relationship cleanup and `#154` - moved /database into /src and updated imports. I also reviewed Jimi’s PR `#163` - updated Git Analyze to support directory input instead of zip and Priyansh's PR `#125` - OS detection for unzip/extraction logic. 

# Week 9 10/27 - 11/02

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week9_log.png)

# Recap on your week goals
This week, my focus was on expanding our analyzer framework to support web development files by implementing CSS, HTML, and PHP analyzers. I worked on Issue `#142`, adding dedicated analyzers for each file type to detect relevant language-specific elements—such as rule blocks and class selectors in CSS, linked resources and scripts in HTML, and functions, classes, and imports in PHP.

I also updated the factory routing in get_appropriate_analyzer() to ensure correct analyzer selection for these new file types and created a full test suite (test_web_analyzers.py) to validate their functionality. This addition enhances our system’s overall analysis coverage and ensures consistent behavior across all supported languages.

Additionally, I reviewed Jimi’s PR for Issue `#78` (extrapolating individual contributions for group projects) and Priyansh’s PR for Issue `#122` (C and TypeScript analyzers).

# Week 8 10/20 - 10/26

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week8_log.png)

# Recap on your week goals
This week, my focus was on implementing a key feature for user-level reporting within our statistics system. I worked on Issue #71: Display a Friendly Representation of UserReport Class, adding a method in the UserReport class to convert stored statistics into readable user-facing messages, along with a full supporting test suite to ensure correct formatting and behavior.

I also reviewed and tested Issue #40: Add File Metadata to FileReport and Issue #68: Generate File Reports After Project Extraction, to help ensure quality and consistency across our codebase. 

# Week 7 10/13 - 10/19

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week7_log.png)

# Recap on your week goals
This week, my focus was on organizing our documentation to support ongoing project tracking. I created a minutes/ directory, uploaded all past meeting notes, and took the notes for our October 16 session to maintain a consistent record of project progress. This centralizes our communication history and sets a clear structure for future documentation. In addition, I participated in our team meeting to discuss upcoming priorities and spent time reviewing my teammates’ code to provide feedback.

# Week 6 10/06 - 10/12

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week6_log.png)

# Recap on your week goals
This week, the main focus was on restructuring the documentation and aligning it with the updated Milestone #1 requirements. I contributed by preparing the team log, summarizing our progress, documenting the changes made to the system architecture and DFDs, and ensuring that our updated goals and deliverables were clearly reflected. This helped maintain consistency across the documentation branch and ensured that our work remained aligned with the revised direction.

# Week 5 09/29 - 10/05

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week5_log.png)

# Recap on your week goals
This week, the main focus was on creating the Level 0 and Level 1 DFD diagrams. I contributed by helping refine the Level 1 and Level 2 diagrams, identifying areas for improvement after presenting to other teams and reviewing their approaches for inspiration.

# Week 4 09/22 - 09/28

# Peer Evaluation!
[Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week4_log.png)

# Recap on your week goals
This week, the main focus was on refining the system architecture diagram and completing the project proposal plan. I helped identify areas for improvement in our architecture diagram after meeting with other groups in the class. For the proposal, I created detailed use case diagrams for viewing the results dashboard and generating a static webpage with the option to host it on GitHub Pages.


# Week 3 09/15 - 09/21

# Peer Evaluation
![Peer Eval THN](./log_images/personal_log_imgs/tawana/tawana_week3_log.png)

# Recap on your week goals
For this week, our main focus was creating the document with the functional and non-functional requirements of the application. I contributed by helping refine the functional and non-functional requirements documents after meeting with other groups in class and comparing approaches. 