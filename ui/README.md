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

Verify installations:
```bash
python3 --version
node -v
npm -v
```
---

# 2. Backend Setup

### 2.1 Installing Backend Dependencies:
From the repository root run:
```
1. python3 -m pip install --upgrade pip
2. python3 -m pip install -r requirements.txt
```

---

### 2.2 Running the FastAPI Server:
From the repository root run:
```
python3 -m fastapi dev ./src/interface/api/api.py
```

# 3. Electron UI Setup

### 3.1 Installing UI Dependencies
From the repository root run:
```
1. cd ui
2. npm install
```

### 3.2 Running Electron UI
From the ui/ directory run:
```
npm run dev
```

---

# 4. Running UI Tests
From the repository root run:
```
cd ui
npx vitest run
```

# 5. Helpful Tips
It is recommended to use two terminal windows:
1. One running the FastAPI backend
2. One running the Electron UI

The Electron UI will display whether it is Connected ✅ or Disconnected ❌ from the backend based on live HTTP requests. 

---

# 6. Stopping The Application
To stop either the backend or the UI, use:
```
Ctrl + C
```
---