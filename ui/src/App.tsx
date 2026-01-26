import { useEffect, useState } from "react";
import { api, getApiBaseUrl } from "./api/apiClient";

export default function App() {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [output, setOutput] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = getApiBaseUrl();

  async function checkConnection() {
    try {
      const ok = await api.ping();
      setConnected(ok);
    } catch {
      setConnected(false);
    }
  }

  async function run<T>(fn: () => Promise<T>) {
    setError(null);
    try {
      const res = await fn();
      setOutput(res);
    } catch (e: any) {
      setOutput(null);
      setError(e?.message ?? "Unknown error");
    }
  }

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ fontFamily: "system-ui", padding: 24, maxWidth: 1000 }}>
      <h1 style={{ marginTop: 0 }}>Capstone UI</h1>

      <div style={{ marginBottom: 10 }}>
        <strong>API Base:</strong> <code>{baseUrl}</code>
      </div>

      <div style={{ marginBottom: 18 }}>
        <strong>Status:</strong>{" "}
        {connected === null ? "checking…" : connected ? "Connected ✅" : "Disconnected ❌"}
        {!connected && (
          <div style={{ marginTop: 8, color: "#666" }}>
            Start the API with: <code>fastapi dev ./src/interface/api/api.py</code>
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <button
          disabled={!connected}
          onClick={() => run(api.getProjects)}
          style={{ padding: "8px 12px" }}
        >
          GET /projects
        </button>

        <button
          disabled={!connected}
          onClick={() => run(api.getSkills)}
          style={{ padding: "8px 12px" }}
        >
          GET /skills
        </button>
      </div>

      {error && (
        <div style={{ marginBottom: 12, color: "crimson" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <pre
        style={{
          background: "#f6f6f6",
          padding: 14,
          borderRadius: 10,
          maxHeight: 450,
          overflow: "auto",
          margin: 0
        }}
      >
        {output ? JSON.stringify(output, null, 2) : "Click an endpoint to load data…"}
      </pre>
    </div>
  );
}