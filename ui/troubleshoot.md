# Electron Troubleshooting

This document provides guidance for handling some common errors that Electron might throw.

---

### Electron refuses to launch or shows `SingletonLock` errors

If Electron crashes or is force-stopped, it may leave behind a stale
singleton lock file and refuse to relaunch.

If you see errors like: `Failed to create ... SingletonLock: File exists`

Run the following to reset Electron, then restart the UI:

```bash
pkill -f Electron
rm -f "$HOME/Library/Application Support/electron-vite-react/SingletonLock"
npm run dev
```

### Unexpected token 'H' ... is not valid JSON
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
3. If `VITE_API_BASE_URL` is defined (e.g., in `ui/.env`), ensure it matches the backend URL.
Otherwise, the UI defaults to `http://127.0.0.1:8000`.

You can also verify the actual request target by opening Electron DevTools → Network tab and inspecting the `/ping` request URL.

### Spawn Unknown system error -8 when running npm run dev
If Electron fails to launch with an error similar to: `Error: spawn Unknown system error -8`, this is typically caused by corrupted `node_modules`, Electron cache issues, or a mismatched Node version.

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
