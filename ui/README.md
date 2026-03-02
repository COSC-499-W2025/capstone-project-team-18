# Electron UI + FastAPI Full Setup Guide

This document outlines the complete local setup process for running and testing the Electron-based UI alongside the FastAPI backend, including required dependencies and commands.

---

## 1. System Requirements

### Supported Operating Systems:
- macOS
- Linux
- Windows (WSL recommended)

### Required Software:
- **Python 3.13 recommended** (3.12 supported/newer versions may have dependency compatibility issues)
- **Node.js 20.0.0+** (required; enforced via `ui/package.json` engines field)

### Verify installations:
```bash
python3 --version
which python3   # should point to your system Python before creating venv
node -v
npm -v
```
---

# 2. Backend Setup

### 2.1 Installing Backend Dependencies:
From the repository root run:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows (PowerShell): .venv\Scripts\Activate.ps1
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 2.2 Running the FastAPI Server:
From the repository root run:
```bash
python3 -m uvicorn src.interface.api.api:app --reload --reload-dir src
```

# 3. Electron UI Setup

### 3.1 Installing UI Dependencies
From the repository root run:
```bash
cd ui
npm install
```

### 3.2 Running Electron UI
From the `ui/` directory run:
```bash
npm run dev
```
Vite will print `http://localhost:5173` for the web renderer. For the Electron app, use the Electron window that opens when running npm run dev.

---

# 4. Running UI Tests

The Electron UI uses Vitest for unit testing instead of Pytest. These tests are frontend-only and do not require the FastAPI backend to be running.

### 4.1 What is Tested:
- API client behavior (URL construction, base URL normalization)
- Correct endpoint calls (`/projects`, `/projects/{project_name}`, `/skills`, `/ping`)
- URL encoding for route parameters (e.g. project names with spaces)
- Error handling for non-200 HTTP responses, including actionable error messages
- Backend connectivity checks independent of database state

### 4.2 How The Tests Work:
- Tests run in a Node/Vitest environment, not in a browser
- `fetch` is mocked using Vitest (`vi.fn()`), so no real HTTP requests are made
- Environment variables (e.g. `VITE_API_BASE_URL`) are injected manually per test
- This keeps UI tests fast, deterministic, and independent from the backend

### 4.3 Running UI Tests Locally:
From the `ui/` directory run:
```bash
npx vitest run
```

### 4.4 Running Tests in GitHub Actions:
UI tests are also executed automatically on pull requests via GitHub Actions. The workflow installs dependencies using npm ci (based on package-lock.json) and runs:
```bash
npx vitest run
```
### 4.5 Future Tests (Guideline):
- Unit tests (Vitest): should mock network calls (`fetch`) and not depend on the backend.
- Integration/End-to-end tests (optional later): can be added separately if we want to validate real backend + UI flows.

---

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

# 7. Troubleshooting

### 7.1 Electron refuses to launch or shows `SingletonLock` errors

If Electron crashes or is force-stopped, it may leave behind a stale
singleton lock file and refuse to relaunch.

If you see errors like: `Failed to create ... SingletonLock: File exists`

Run the following to reset Electron, then restart the UI:

```bash
pkill -f Electron
rm -f "$HOME/Library/Application Support/electron-vite-react/SingletonLock"
npm run dev
```

### 7.2 Unexpected token 'H' ... is not valid JSON
If you see an error like:  
`Uncaught (in promise) SyntaxError: Unexpected token 'H', "HTTP/1.1 4"... is not valid JSON`, this usually means the UI attempted to parse a non-JSON HTTP response.

Common causes:
1. The FastAPI backend is not running
2. The UI is pointing to the wrong backend URL or port.
3. The backend returned an HTML error page (e.g., 404/500) instead of JSON.

Fix:
1. Ensure the backend is running:
```bash
python3 -m uvicorn src.interface.api.api:app --reload --reload-dir src
```
2. Confirm the backend responds with: `http://127.0.0.1:8000/ping`
3. If VITE_API_BASE_URL is defined (e.g., in ui/.env), ensure it matches the backend URL.
Otherwise, the UI defaults to `http://127.0.0.1:8000`.

You can also verify the actual request target by opening Electron DevTools → Network tab and inspecting the /ping request URL.

### 7.3 spawn Unknown system error -8 when running npm run dev
If Electron fails to launch with an error similar to: `Error: spawn Unknown system error -8`, this is typically caused by corrupted node_modules, Electron cache issues, or a mismatched Node version.

Fix:
1. From the ui/ directory run:
```bash
rm -rf node_modules package-lock.json
npm cache verify   # or: npm cache clean --force
npm install
npm run dev
```
2. Ensure you are running Node 20.0.0 or newer
```bash
node -v
```
---

# 8. TODO / Future Improvements

### 8.1 Content Security Policy (CSP) Hardening

During development, Electron may log a warning about an insecure or missing
Content Security Policy (CSP), often due to the use of Vite hot module
reloading and development tooling that relies on `unsafe-eval`.

This warning is expected in development mode and does not block functionality. It typically does not appear (or is different) once the app is packaged for
production.

**Planned improvements:**
- Define an explicit CSP for the Electron renderer process
- Remove `unsafe-eval` and other overly permissive directives in production
- Align CSP rules with packaged Electron assets (`file://`) instead of dev URLs
- Document production vs development CSP differences

These changes will be addressed when preparing the app for production builds.

---