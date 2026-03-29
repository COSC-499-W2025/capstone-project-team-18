import { useEffect, useRef, useState } from "react";
import { api } from "../api/apiClient";

const SKILL_LABELS: Record<number, string> = {
  1: "Beginner",
  2: "Basic",
  3: "Intermediate",
  4: "Advanced",
  5: "Expert",
};

const SKILL_LABEL_TO_NUM: Record<string, number> = {
  Beginner: 1,
  Basic: 2,
  Intermediate: 3,
  Advanced: 4,
  Expert: 5,
};

type RatedSkill = { name: string; rating: number };

type GithubAuthStatus = "idle" | "pending" | "success" | "denied" | "error";

export default function ProfilePage() {
  const [name, setName] = useState("");
  const [github, setGithub] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [mlConsent, setMlConsent] = useState(false);

  const [education, setEducation] = useState<string[]>([]);
  const [educationInput, setEducationInput] = useState("");
  const [awards, setAwards] = useState<string[]>([]);
  const [awardInput, setAwardInput] = useState("");
  const [skills, setSkills] = useState<RatedSkill[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [skillRating, setSkillRating] = useState<number>(3);

  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [githubConnected, setGithubConnected] = useState(false);
  const [githubAuthStatus, setGithubAuthStatus] = useState<GithubAuthStatus>("idle");
  const [githubAuthDetail, setGithubAuthDetail] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const oauthStateRef = useRef<string | null>(null);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

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
    let alive = true;

    async function loadUserConfig() {
      try {
        setIsLoadingConfig(true);
        setError(null);
        setSuccess(null);

        const res = await api.getUserConfig();

        if (!alive) return;

        setName(res?.name ?? "");
        setGithub(res?.github ?? "");
        setEmail(res?.user_email ?? "");
        setConsent(Boolean(res?.consent));
        setEducation(res?.resume_config?.education ?? []);
        setAwards(res?.resume_config?.awards ?? []);
        setSkills(
          (res?.resume_config?.skills ?? []).map((s: string) => {
            const lastColon = s.lastIndexOf(":");
            const name = lastColon >= 0 ? s.slice(0, lastColon) : s;
            const label = lastColon >= 0 ? s.slice(lastColon + 1) : "Intermediate";
            const rating = SKILL_LABEL_TO_NUM[label] ?? (parseInt(label, 10) || 3);
            return { name, rating };
          })
        );
        setMlConsent(Boolean(res?.ml_consent));
        setGithubConnected(Boolean(res?.github_connected));
      } catch (e: any) {
        if (!alive) return;

        setName("");
        setGithub("");
        setEmail("");
        setConsent(false);
        setEducation([]);
        setAwards([]);
        setSkills([]);
        setMlConsent(false);
        setError(e?.message ?? "Failed to load saved settings.");
      } finally {
        if (alive) setIsLoadingConfig(false);
      }
    }

    loadUserConfig();

    return () => {
      alive = false;
    };
  }, []);

  const emailIsValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const githubIsValid = /^(?!-)[A-Za-z0-9-]{1,39}(?<!-)$/.test(github.trim());
  const githubOk = github.trim() === "" || githubIsValid;
  const isValid = githubOk && emailIsValid && consent;

  function handleConsentChange(checked: boolean) {
    setConsent(checked);
    if (!checked) {
      setMlConsent(false);
    }
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
        ml_consent: consent && mlConsent,
        name: name.trim() || null,
        user_email: email.trim(),
        github: github.trim(),
        resume_config: {
          education,
          awards,
          skills: skills.map((s) => `${s.name}:${SKILL_LABELS[s.rating] ?? "Intermediate"}`),
        },
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

      await (window as any).ipcRenderer?.invoke("open-external", authorization_url);

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
      }, 2000);
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
    <div style={{ padding: 24, paddingTop: 40, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Profile</h1>
        <p style={{ marginTop: 8, color: "#aaa" }}>
          Manage your display name, education, awards, skills, GitHub access, and consent settings.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: 20,
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleSave();
          }}
          style={{
            background: "#1b1b1b",
            borderRadius: 16,
            padding: 24,
            border: "1px solid #2a2a2a",
          }}
        >
          <h2 style={{ marginTop: 0, marginBottom: 16 }}>User Information</h2>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "#aaa" }}>Name (optional)</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Paula Atreides"
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
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "#aaa" }}>Education (optional)</label>
            <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
              <input
                value={educationInput}
                onChange={(e) => setEducationInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && educationInput.trim()) {
                    setEducation((prev) => [...prev, educationInput.trim()]);
                    setEducationInput("");
                  }
                }}
                placeholder="e.g. BSc Computer Science, UBC, 2024"
                disabled={isSaving || isLoadingConfig}
                style={{
                  flex: 1,
                  padding: 10,
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "#111",
                  color: "#fff",
                }}
              />
              <button
                type="button"
                onClick={() => {
                  if (educationInput.trim()) {
                    setEducation((prev) => [...prev, educationInput.trim()]);
                    setEducationInput("");
                  }
                }}
                disabled={isSaving || isLoadingConfig || !educationInput.trim()}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "#2b2b2b",
                  color: "#fff",
                  cursor: "pointer",
                }}
              >
                Add
              </button>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              {education.map((entry, i) => (
                <span
                  key={i}
                  style={{
                    background: "#2a2a2a",
                    borderRadius: 6,
                    padding: "4px 10px",
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {entry}
                  <button
                    type="button"
                    onClick={() => setEducation((prev) => prev.filter((_, j) => j !== i))}
                    disabled={isSaving || isLoadingConfig}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#aaa",
                      cursor: "pointer",
                      padding: 0,
                      lineHeight: 1,
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "#aaa" }}>Awards (optional)</label>
            <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
              <input
                value={awardInput}
                onChange={(e) => setAwardInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && awardInput.trim()) {
                    setAwards((prev) => [...prev, awardInput.trim()]);
                    setAwardInput("");
                  }
                }}
                placeholder="e.g. Dean's List 2023"
                disabled={isSaving || isLoadingConfig}
                style={{
                  flex: 1,
                  padding: 10,
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "#111",
                  color: "#fff",
                }}
              />
              <button
                type="button"
                onClick={() => {
                  if (awardInput.trim()) {
                    setAwards((prev) => [...prev, awardInput.trim()]);
                    setAwardInput("");
                  }
                }}
                disabled={isSaving || isLoadingConfig || !awardInput.trim()}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "#2b2b2b",
                  color: "#fff",
                  cursor: "pointer",
                }}
              >
                Add
              </button>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              {awards.map((award, i) => (
                <span
                  key={i}
                  style={{
                    background: "#2a2a2a",
                    borderRadius: 6,
                    padding: "4px 10px",
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {award}
                  <button
                    type="button"
                    onClick={() => setAwards((prev) => prev.filter((_, j) => j !== i))}
                    disabled={isSaving || isLoadingConfig}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#aaa",
                      cursor: "pointer",
                      padding: 0,
                      lineHeight: 1,
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 0 }}>
            <label style={{ fontSize: 14, color: "#aaa" }}>Skills (optional)</label>
            <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
              <input
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && skillInput.trim()) {
                    setSkills((prev) => [...prev, { name: skillInput.trim(), rating: skillRating }]);
                    setSkillInput("");
                    setSkillRating(3);
                  }
                }}
                placeholder="e.g. Python"
                disabled={isSaving || isLoadingConfig}
                style={{
                  flex: 1,
                  padding: 10,
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "#111",
                  color: "#fff",
                }}
              />
              <select
                value={skillRating}
                onChange={(e) => setSkillRating(Number(e.target.value))}
                disabled={isSaving || isLoadingConfig}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "#111",
                  color: "#fff",
                  fontSize: 13,
                }}
              >
                <option value={1}>Beginner</option>
                <option value={2}>Basic</option>
                <option value={3}>Intermediate</option>
                <option value={4}>Advanced</option>
                <option value={5}>Expert</option>
              </select>
              <button
                type="button"
                onClick={() => {
                  if (skillInput.trim()) {
                    setSkills((prev) => [...prev, { name: skillInput.trim(), rating: skillRating }]);
                    setSkillInput("");
                    setSkillRating(3);
                  }
                }}
                disabled={isSaving || isLoadingConfig || !skillInput.trim()}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "#2b2b2b",
                  color: "#fff",
                  cursor: "pointer",
                }}
              >
                Add
              </button>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              {skills.map((sk, i) => (
                <span
                  key={i}
                  style={{
                    background: "#2a2a2a",
                    borderRadius: 6,
                    padding: "4px 10px",
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {sk.name}
                  <span
                    style={{
                      fontSize: 11,
                      color: "#888",
                      background: "#1a1a1a",
                      borderRadius: 4,
                      padding: "1px 5px",
                    }}
                  >
                    {SKILL_LABELS[sk.rating] ?? "Intermediate"}
                  </span>
                  <button
                    type="button"
                    onClick={() => setSkills((prev) => prev.filter((_, j) => j !== i))}
                    disabled={isSaving || isLoadingConfig}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#aaa",
                      cursor: "pointer",
                      padding: 0,
                      lineHeight: 1,
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                marginTop: 16,
                paddingTop: 12,
                borderTop: "1px solid #2a2a2a",
              }}
            >
              <button
                type="submit"
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
        </form>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleSave();
          }}
          style={{
            background: "#1b1b1b",
            borderRadius: 16,
            padding: 24,
            border: "1px solid #2a2a2a",
          }}
        >
          <h2 style={{ marginTop: 0, marginBottom: 16 }}>Settings</h2>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "#aaa" }}>GitHub Access</label>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
              {githubConnected ? (
                <button
                  type="button"
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
                  type="button"
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

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "#aaa" }}>Email *</label>
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

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "#aaa" }}>GitHub Username (optional)</label>
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

          <div
            style={{
              marginBottom: 16,
              padding: 14,
              borderRadius: 12,
              border: "1px solid #2a2a2a",
              background: "#141414",
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                fontSize: 14,
                marginBottom: 10,
              }}
            >
              <input
                type="checkbox"
                checked={consent}
                disabled={isSaving || isLoadingConfig}
                onChange={(e) => handleConsentChange(e.target.checked)}
              />
              <span>
                <strong style={{ display: "block", color: "#f1f1f1" }}>
                  I consent to project data processing for mining *
                </strong>
                <span style={{ color: "#aaa", lineHeight: 1.5 }}>
                  This allows the app to analyze your project files and Git data to generate reports and portfolio content.
                </span>
              </span>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                fontSize: 14,
                opacity: consent ? 1 : 0.6,
              }}
            >
              <input
                type="checkbox"
                checked={mlConsent}
                disabled={!consent || isSaving || isLoadingConfig}
                onChange={(e) => setMlConsent(e.target.checked)}
              />
              <span>
                <strong style={{ display: "block", color: consent ? "#f1f1f1" : "#888" }}>
                  I also consent to ML-assisted analysis
                </strong>
                <span style={{ color: "#aaa", lineHeight: 1.5 }}>
                  Optional. This lets the app use ML for deeper analysis on top of the base project mining above.
                </span>
                {!consent && (
                  <span style={{ display: "block", color: "#888", marginTop: 4 }}>
                    Enable project data processing first to choose ML-assisted analysis.
                  </span>
                )}
              </span>
            </label>

            {email.trim() !== "" && !consent && (
              <div style={{ color: "#ff8a8a", fontSize: 13, marginTop: 6 }}>
                Please provide consent to enable saving
              </div>
            )}
          </div>

          {error && <div style={{ color: "#ff8a8a", marginBottom: 12 }}>{error}</div>}
          {success && <div style={{ color: "#8ad6a2", marginBottom: 12 }}>{success}</div>}

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

            <button
              type="submit"
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
        </form>
      </div>
    </div>
  );
}
