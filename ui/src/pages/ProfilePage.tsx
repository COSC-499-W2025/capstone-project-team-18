import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { api } from "../api/apiClient";

const SKILL_LABELS: Record<number, string> = {
  1: "Exposure",
  2: "Intermediate",
  3: "Expert",
};

const SKILL_LABEL_TO_NUM: Record<string, number> = {
  Exposure: 1,
  Intermediate: 2,
  Expert: 3,
};

type RatedSkill = { name: string; rating: number };

type GithubAuthStatus = "idle" | "pending" | "success" | "denied" | "error";

export default function ProfilePage() {
  const location = useLocation();
  const [consentBanner, setConsentBanner] = useState(
    () => (location.state as any)?.consentRequired === true
  );
  const consentSectionRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!consentBanner) return;
    const timer = setTimeout(() => {
      consentSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 100);
    return () => clearTimeout(timer);
  }, [consentBanner]);
  const location = useLocation();
  const [consentBanner, setConsentBanner] = useState(
    () => (location.state as any)?.consentRequired === true
  );
  const consentSectionRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!consentBanner) return;
    const timer = setTimeout(() => {
      consentSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 100);
    return () => clearTimeout(timer);
  }, [consentBanner]);
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
  const [skillRating, setSkillRating] = useState<number>(2);

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
    if (!checked) setMlConsent(false);
    if (checked) setConsentBanner(false);
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

      setSuccess("Changes saved successfully.");
    } catch (e: any) {
      setError(e?.message ?? "Failed to save changes.");
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
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: 20,
        }}
      >
        <div
          style={{
            background: "var(--bg-surface)",
            borderRadius: 16,
            padding: "24px 32px",
            border: "1px solid var(--border)",
          }}
        >
          <h2 style={{ marginTop: 0, marginBottom: 4 }}>User Information</h2>
          <p style={{ marginTop: 0, marginBottom: 16, color: "var(--text-muted)", fontSize: 14 }}>
            Manage your resume's display name, education, awards, and skills.
          </p>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "var(--text-muted)" }}>Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Paul Atreides"
              disabled={isSaving || isLoadingConfig}
              style={{
                width: "100%",
                marginTop: 6,
                padding: 10,
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--bg-input)",
                color: "var(--text-primary)",
              }}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "var(--text-muted)" }}>Education</label>
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
                  border: "1px solid var(--border)",
                  background: "var(--bg-input)",
                  color: "var(--text-primary)",
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
                  border: "1px solid var(--border)",
                  background: "var(--accent)",
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
                    background: "var(--bg-surface-deep)",
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
                      color: "var(--text-muted)",
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
            <label style={{ fontSize: 14, color: "var(--text-muted)" }}>Awards</label>
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
                  border: "1px solid var(--border)",
                  background: "var(--bg-input)",
                  color: "var(--text-primary)",
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
                  border: "1px solid var(--border)",
                  background: "var(--accent)",
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
                    background: "var(--bg-surface-deep)",
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
                      color: "var(--text-muted)",
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
            <label style={{ fontSize: 14, color: "var(--text-muted)" }}>Skills</label>
            <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
              <input
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && skillInput.trim()) {
                    setSkills((prev) => [...prev, { name: skillInput.trim(), rating: skillRating }]);
                    setSkillInput("");
                    setSkillRating(2);
                  }
                }}
                placeholder="e.g. Python"
                disabled={isSaving || isLoadingConfig}
                style={{
                  flex: 1,
                  padding: 10,
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--bg-input)",
                  color: "var(--text-primary)",
                }}
              />
              <select
                value={skillRating}
                onChange={(e) => setSkillRating(Number(e.target.value))}
                disabled={isSaving || isLoadingConfig}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--bg-input)",
                  color: "var(--text-primary)",
                  fontSize: 13,
                }}
              >
                <option value={1}>Exposure</option>
                <option value={2}>Intermediate</option>
                <option value={3}>Expert</option>
              </select>
              <button
                type="button"
                onClick={() => {
                  if (skillInput.trim()) {
                    setSkills((prev) => [...prev, { name: skillInput.trim(), rating: skillRating }]);
                    setSkillInput("");
                    setSkillRating(2);
                  }
                }}
                disabled={isSaving || isLoadingConfig || !skillInput.trim()}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--accent)",
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
                    background: "var(--bg-surface-deep)",
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
                      color: "var(--text-muted)",
                      background: "var(--bg-surface-deep)",
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
                      color: "var(--text-muted)",
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
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleSave();
          }}
          style={{
            background: "var(--bg-surface)",
            borderRadius: 16,
            padding: "24px 32px",
            border: "1px solid var(--border)",
          }}
        >
          <h2 style={{ marginTop: 0, marginBottom: 4 }}>Settings</h2>
          <p style={{ marginTop: 0, marginBottom: 16, color: "var(--text-muted)", fontSize: 14 }}>
            GitHub access, Git-related analysis, and AI consent.
          </p>

          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
              {githubConnected ? (
                <button
                  type="button"
                  onClick={handleGithubDisconnect}
                  disabled={isSaving || isLoadingConfig}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 8,
                    border: "none",
                    background: "#dc2626",
                    color: "#fff",
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
              <span style={{ fontSize: 13, color: githubConnected ? "#16a34a" : "var(--text-muted)" }}>
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
            <label style={{ fontSize: 14, color: "var(--text-muted)" }}>Email*</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="patreides@email.com"
              disabled={isSaving || isLoadingConfig}
              style={{
                width: "100%",
                marginTop: 6,
                padding: 10,
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--bg-input)",
                color: "var(--text-primary)",
              }}
            />
            {email && !emailIsValid && (
              <div style={{ color: "var(--danger-text)", fontSize: 13, marginTop: 6 }}>
                Please enter a valid email (e.g. example@gmail.com)
              </div>
            )}
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 14, color: "var(--text-muted)" }}>GitHub Username</label>
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
                border: "1px solid var(--border)",
                background: "var(--bg-input)",
                color: "var(--text-primary)",
              }}
            />
            {github && !githubIsValid && (
              <div style={{ color: "var(--danger-text)", fontSize: 13, marginTop: 6 }}>
                Please enter a valid GitHub username (e.g. paulatreides)
              </div>
            )}
          </div>

          {consentBanner && (
            <>
              <style>{`
                @keyframes slideDown {
                  from { opacity: 0; transform: translateY(-10px); }
                  to   { opacity: 1; transform: translateY(0); }
                }
                @keyframes consentPulse {
                  0%   { box-shadow: 0 0 0 0    rgba(217,119,6,0.5); }
                  60%  { box-shadow: 0 0 0 10px rgba(217,119,6,0); }
                  100% { box-shadow: 0 0 0 0    rgba(217,119,6,0); }
                }
              `}</style>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 10,
                  background: "#fef3c7",
                  border: "1px solid #d97706",
                  borderRadius: 10,
                  padding: "10px 14px",
                  marginBottom: 12,
                  fontSize: 14,
                  color: "#92400e",
                  animation: "slideDown 0.4s ease",
                }}
              >
                <span>You must enter your email and accept the data consent below before you can mine a project.</span>
                <button
                  type="button"
                  onClick={() => setConsentBanner(false)}
                  style={{
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "#92400e",
                    fontSize: 18,
                    lineHeight: 1,
                    flexShrink: 0,
                  }}
                  aria-label="Dismiss"
                >
                  ×
                </button>
              </div>
            </>
          )}

          <div
            ref={consentSectionRef}
            style={{
              marginBottom: 16,
              padding: 14,
              borderRadius: 12,
              border: consentBanner ? "1px solid #d97706" : "1px solid var(--border)",
              background: "var(--bg-surface-deep)",
              animation: consentBanner ? "consentPulse 1.4s ease 0.4s 3" : undefined,
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
                <strong style={{ display: "block", color: "var(--text-primary)" }}>
                  I consent to project data processing for mining *
                </strong>
                <span style={{ color: "var(--text-muted)", lineHeight: 1.5 }}>
                  Allow the app to analyze your project files and Git data to generate resume and portfolio content.
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
                <strong style={{ display: "block", color: consent ? "var(--text-primary)" : "var(--text-muted)" }}>
                  I consent to AI-assisted analysis and features.
                </strong>
                <span style={{ color: "var(--text-muted)", lineHeight: 1.5 }}>
                  Enable the use of AI for more in-depth project analysis and features such as an AI-generated portfolio summary.
                </span>
                {!consent && (
                  <span style={{ display: "block", color: "var(--text-muted)", marginTop: 4 }}>
                    Enable project data processing first to choose AI-assisted analysis.
                  </span>
                )}
              </span>
            </label>

            {email.trim() !== "" && !consent && (
              <div style={{ color: "var(--danger-text)", fontSize: 13, marginTop: 6 }}>
                Please provide consent to enable saving
              </div>
            )}
          </div>

          {error && <div style={{ color: "var(--danger-text)", marginBottom: 12 }}>{error}</div>}
          {success && <div style={{ color: "#16a34a", marginBottom: 12 }}>{success}</div>}

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
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
                background: isValid ? "var(--accent)" : "var(--bg-surface-deep)",
                color: isValid ? "#fff" : "var(--text-muted)",
                fontWeight: 600,
                cursor: isValid ? "pointer" : "not-allowed",
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
