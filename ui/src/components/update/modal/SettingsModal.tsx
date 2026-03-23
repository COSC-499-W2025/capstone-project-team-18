import { useEffect, useRef, useState } from "react";
import { api } from "../../../api/apiClient";

type SettingsModalProps = {
  open: boolean;
  onClose: () => void;
};

export default function SettingsModal({ open, onClose }: SettingsModalProps) {
  const [github, setGithub] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);

  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [githubConnected, setGithubConnected] = useState(false);
  const [githubAuthStatus, setGithubAuthStatus] = useState<"idle" | "pending" | "success" | "denied" | "error">("idle");
  const [githubAuthDetail, setGithubAuthDetail] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const oauthStateRef = useRef<string | null>(null);

  // Listen for the deep-link callback from Electron main process
  useEffect(() => {
    function onOauthCallback(_event: any, payload: { state: string; status: string; detail: string | null }) {
      if (payload.state !== oauthStateRef.current) return;
      stopPolling();
      const status = payload.status as "success" | "denied" | "error";
      setGithubAuthStatus(status);
      setGithubAuthDetail(payload.detail ?? null);
      if (status === "success") setGithubConnected(true);
    }

    (window as any).ipcRenderer?.on("github-oauth-callback", onOauthCallback);
    return () => {
      (window as any).ipcRenderer?.off("github-oauth-callback", onOauthCallback);
      stopPolling();
    };
  }, []);

  useEffect(() => {
    if (!open) return;

    let alive = true;

    async function loadUserConfig() {
      try {
        setIsLoadingConfig(true);
        setError(null);
        setSuccess(null);

        const res = await api.getUserConfig();

        if (!alive) return;

        setGithub(res?.github ?? "");
        setEmail(res?.user_email ?? "");
        setConsent(Boolean(res?.consent));
        setGithubConnected(Boolean(res?.github_connected));
      } catch (e: any) {
        if (!alive) return;

        setGithub("");
        setEmail("");
        setConsent(false);
        setError(e?.message ?? "Failed to load saved settings.");
      } finally {
        if (alive) setIsLoadingConfig(false);
      }
    }

    loadUserConfig();

    return () => {
      alive = false;
    };
  }, [open]);

  if (!open) return null;

  const emailIsValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const githubIsValid = /^(?!-)[A-Za-z0-9-]{1,39}(?<!-)$/.test(github.trim());
  const githubOk = github.trim() === "" || githubIsValid;
  const isValid = githubOk && emailIsValid && consent;

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function handleClose() {
    if (isSaving || isLoadingConfig) return;
    stopPolling();
    onClose();
  }

  async function handleSave() {
    setError(null);
    setSuccess(null);

    if (!isValid) {
      setError("Please fix the highlighted fields before saving.");
      return;
    }

    try {
      setIsSaving(true);

      await api.updateUserConfig({
        consent,
        user_email: email.trim(),
        github: github.trim(),
      });

      setSuccess("Settings saved successfully.");
    } catch (e: any) {
      setError(e?.message ?? "Failed to save settings.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleGithubConnect() {
    setGithubAuthStatus("pending");
    setGithubAuthDetail(null);
    setError(null);

    try {
      const { state, authorization_url } = await api.githubLogin();
      oauthStateRef.current = state;

      // Open the GitHub auth page in the OS browser
      await (window as any).ipcRenderer?.invoke("open-external", authorization_url);

      // Poll backend until the OAuth flow completes (deep link also notifies us)
      pollRef.current = setInterval(async () => {
        try {
          const result = await api.githubOauthStatus(state);
          if (result.status !== "pending") {
            stopPolling();
            setGithubAuthStatus(result.status);
            setGithubAuthDetail(result.detail ?? null);
            if (result.status === "success") {
              setGithubConnected(true);
            }
          }
        } catch {
          // keep polling on transient errors
        }
      }, 2000); // every 2000ms = 2 sec
    } catch (e: any) {
      setGithubAuthStatus("error");
      setGithubAuthDetail(e?.message ?? "Failed to start GitHub login");
    }
  }

  async function handleGithubDisconnect() {
    setError(null);
    try {
      await api.revokeGithubToken();
      setGithubConnected(false);
      setGithubAuthStatus("idle");
      setGithubAuthDetail(null);
      await (window as any).ipcRenderer?.invoke("open-external", "https://github.com/settings/applications");
    } catch (e: any) {
      setError(e?.message ?? "Failed to disconnect GitHub");
    }
  }

  return (
    <div
      onClick={handleClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        zIndex: 1000,
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 600,
          background: "#1b1b1b",
          borderRadius: 16,
          padding: 24,
          border: "1px solid #2a2a2a",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 20,
          }}
        >
          <h2 style={{ margin: 0 }}>Settings</h2>

          <button
            onClick={handleClose}
            disabled={isSaving || isLoadingConfig}
            style={{
              background: "transparent",
              border: "none",
              color: "#ccc",
              fontSize: 20,
              cursor: isSaving || isLoadingConfig ? "not-allowed" : "pointer",
            }}
          >
            ×
          </button>
        </div>

        {/* GitHub */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 14, color: "#aaa" }}>
            GitHub Username (optional)
          </label>
          <input
            value={github}
            onChange={(e) => setGithub(e.target.value)}
            placeholder="e.g. paulatreides"
            disabled={isSaving || isLoadingConfig}
            style={{
              width: "100%",
              marginTop: 6,
              padding: 10,
              borderRadius: 8,
              border: "1px solid #2a2a2a",
              background: "#111",
              color: "#fff",
            }}
          />
          {github && !githubIsValid && (
            <div style={{ color: "#ff8a8a", fontSize: 13, marginTop: 6 }}>
                Please enter a valid GitHub username (e.g. paulatreides)
                </div>
            )}
        </div>

        {/* GitHub OAuth */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 14, color: "#aaa" }}>GitHub Access</label>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
            {githubConnected ? (
              <button
                onClick={handleGithubDisconnect}
                disabled={isSaving || isLoadingConfig}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid #444",
                  background: "transparent",
                  color: "#ff8a8a",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                Disconnect GitHub
              </button>
            ) : (
              <button
                onClick={handleGithubConnect}
                disabled={isSaving || isLoadingConfig || githubAuthStatus === "pending"}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "none",
                  background: githubAuthStatus === "pending" ? "#222" : "#238636",
                  color: "#fff",
                  cursor: githubAuthStatus === "pending" ? "not-allowed" : "pointer",
                  fontSize: 13,
                  opacity: githubAuthStatus === "pending" ? 0.7 : 1,
                }}
              >
                {githubAuthStatus === "pending" ? "Waiting for GitHub..." : "Connect GitHub"}
              </button>
            )}
            <span style={{ fontSize: 13, color: githubConnected ? "#8ad6a2" : "#888" }}>
              {githubConnected
                ? "Connected"
                : githubAuthStatus === "pending"
                ? "Authorize in your browser"
                : githubAuthStatus === "denied"
                ? "Access denied"
                : githubAuthStatus === "error"
                ? `Error: ${githubAuthDetail ?? "unknown"}`
                : "Not connected"}
            </span>
          </div>
        </div>

        {/* Email */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 14, color: "#aaa" }}>
            Email *
          </label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            disabled={isSaving || isLoadingConfig}
            style={{
              width: "100%",
              marginTop: 6,
              padding: 10,
              borderRadius: 8,
              border: "1px solid #2a2a2a",
              background: "#111",
              color: "#fff",
            }}
          />
          {email && !emailIsValid && (
            <div style={{ color: "#ff8a8a", fontSize: 13, marginTop: 6 }}>
                Please enter a valid email (e.g. example@gmail.com)
                </div>
            )}
        </div>

        {/* Consent */}
        <div
          style={{
            marginBottom: 16,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <input
            type="checkbox"
            checked={consent}
            disabled={isSaving || isLoadingConfig}
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span style={{ fontSize: 14 }}>
            I consent to data processing for project mining *
          </span>

          {email.trim() !== "" && !consent && (
            <div style={{ color: "#ff8a8a", fontSize: 13, marginTop: 6 }}>
                Please provide consent to enable saving
                </div>
            )}
        </div>

        {/* Errors / Success */}
        {error && (
          <div style={{ color: "#ff8a8a", marginBottom: 12 }}>
            {error}
          </div>
        )}

        {success && (
          <div style={{ color: "#8ad6a2", marginBottom: 12 }}>
            {success}
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ fontSize: 13, color: "#888" }}>
            {isLoadingConfig
              ? "Loading saved settings..."
              : isSaving
              ? "Saving..."
              : "Fill all required fields"}
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleClose}
              disabled={isSaving || isLoadingConfig}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: "transparent",
                border: "1px solid #2a2a2a",
                color: "#ddd",
              }}
            >
              Cancel
            </button>

            <button
              onClick={handleSave}
              disabled={!isValid || isSaving || isLoadingConfig}
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                border: "none",
                background: isValid ? "#2b2b2b" : "#202020",
                color: "#fff",
                opacity: isValid ? 1 : 0.6,
              }}
            >
              {isSaving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}