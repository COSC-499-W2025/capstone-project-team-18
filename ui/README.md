# Electron UI + FastAPI Full Setup Guide

This document outlines the complete local setup process for running and testing the Electron-based UI alongside the FastAPI backend, including required dependencies and commands.

---

## 1. System Requirements

### Supported Operating Systems:
- macOS
- Linux
- Windows (WSL recommended)

### Required Software:
- **Python 3.12+**
- **Node.js 20+** (includes npm)

### Verify installations:
```bash
python3 --version
node -v
npm -v
```
---

# 2. Backend Setup

### 2.1 Installing Backend Dependencies:
From the repository root run:
```bash
1. python3 -m pip install --upgrade pip
2. python3 -m pip install -r requirements.txt
```

---

### 2.2 Running the FastAPI Server:
From the repository root run:
```bash
python3 -m fastapi dev ./src/interface/api/api.py
```

# 3. Electron UI Setup

### 3.1 Installing UI Dependencies
From the repository root run:
```bash
1. cd ui
2. npm install
```

### 3.2 Running Electron UI
From the `ui/` directory run:
```bash
npm run dev
```

---

# 4. Running UI Tests
From the repository root run:
```bash
cd ui
npx vitest run
```

# 5. Helpful Tips
It is recommended to use two terminal windows:
1. One running the FastAPI backend
2. One running the Electron UI

The Electron UI will display whether it is Connected ✅ or Disconnected ❌ from the backend using a lightweight `GET /ping` check, decoupled from database-backed endpoints. 

---

# 6. Stopping The Application
To stop either the backend or the UI, use:
```bash
Ctrl + C
```
---

# 7. Running UI Tests

The Electron UI uses Vitest for unit testing instead of Pytest. These tests are frontend-only and do not require the FastAPI backend to be running.

### 7.1 What is Tested:
- API client behavior (URL construction, base URL normalization)
- Correct endpoint calls (`/projects`, `/projects/{project_name}`, `/skills`, `/ping`)
- URL encoding for route parameters (e.g. project names with spaces)
- Error handling for non-200 HTTP responses, including actionable error messages
- Backend connectivity checks independent of database state

### 7.2 How The Tests Work:
- Tests run in a Node/Vitest environment, not in a browser
- `fetch` is mocked using Vitest (`vi.fn()`), so no real HTTP requests are made
- Environment variables (e.g. `VITE_API_BASE_URL`) are injected manually per test
- This keeps UI tests fast, deterministic, and independent from the backend

### 7.3 Running UI Tests Locally:
From the `ui/` directory run:
```bash
npx vitest run
```

### 7.4 Running Tests in GitHub Actions:
UI tests are also executed automatically on pull requests via GitHub Actions. The workflow installs dependencies using npm ci (based on package-lock.json) and runs:
```bash
npx vitest run
```
### 7.5 Future Tests (Guideline):
- Unit tests (Vitest): should mock network calls (`fetch`) and not depend on the backend.
- Integration/End-to-end tests (optional later): can be added separately if we want to validate real backend + UI flows.

---