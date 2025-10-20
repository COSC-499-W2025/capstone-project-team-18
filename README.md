```
.         
├── src                     # Source files (alternatively `app`)
├── tests                   # Automated tests 
├── utils                   # Utility files
└── README.md
```

Please use a branching workflow, and once an item is ready, do remember to issue a PR, review, and merge it into the master branch.
Be sure to keep your docs and README.md up-to-date.


# Branches 

There are three sub-branches (off of main) in this project:
1. [develop](https://github.com/COSC-499-W2025/capstone-project-team-18/tree/develop) — Branch off of here when developing features / making changes to the codebase
2. [doc](https://github.com/COSC-499-W2025/capstone-project-team-18/tree/doc) — All documentation should be located here (e.g. system architecture, project plan)
3. [log](https://github.com/COSC-499-W2025/capstone-project-team-18/tree/log) — All weekly personal logs and the team's log are located here.


## CLI Tool: Project Artifact Miner

We are building a command‑line interface (CLI) tool for mining project artifacts. The CLI entrypoint lives in `src/app.py` and uses Python's standard `cmd` module to provide an interactive prompt.

### How to run

Prerequisites: Python 3.11+ recommended.

1. (Optional) Create and activate a virtual environment
   - macOS/Linux:
     - `python3 -m venv .venv`
     - `source .venv/bin/activate`
   - Windows (PowerShell):
     - `py -m venv .venv`
     - `.venv\\Scripts\\Activate.ps1`
2. Install dependencies: `pip install -r requirements.txt`
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

