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

