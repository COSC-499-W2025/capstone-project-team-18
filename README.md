# CLI User Guide

## Quick Start
```bash
cd src
python3 app.py
```

## Commands
| Input | Action |
|-------|--------|
| `1` | Grant permissions |
| `2` | Set file path |
| `3` | Begin analysis |
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
Requires steps 1 & 2 completed first.

## Example Session
```bash
(PAF) 1
(Y/N): Y
Thank you for consenting.

(PAF) 2
Enter filepath: ./myproject
Filepath successfully received

(PAF) 3
[Analysis begins...]
```

## Error Messages
- **"Missing consent"** → Complete step 1
- **"Invalid file"** → Check file path in step 2
- **"Unknown command"** → Use 1, 2, 3, or help

## Testing
```bash
cd tests
python3 test_app_cli.py
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

