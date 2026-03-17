import { useState } from "react";

type SettingsModalProps = {
  open: boolean;
  onClose: () => void;
};

export default function SettingsModal({ open, onClose }: SettingsModalProps) {
  const [github, setGithub] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!open) return null;

  const emailIsValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const githubIsValid = /^(?!-)[A-Za-z0-9-]{1,39}(?<!-)$/.test(github.trim());
  const isValid = githubIsValid && emailIsValid && consent;

  function handleClose() {
    if (isSaving) return;
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

      // Placeholder for backend
      await new Promise((res) => setTimeout(res, 800));

      setSuccess("Settings saved (frontend only). Ready for backend hookup.");
    } catch (e: any) {
      setError(e?.message ?? "Failed to save settings.");
    } finally {
      setIsSaving(false);
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
            disabled={isSaving}
            style={{
              background: "transparent",
              border: "none",
              color: "#ccc",
              fontSize: 20,
              cursor: "pointer",
            }}
          >
            ×
          </button>
        </div>

        {/* GitHub */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 14, color: "#aaa" }}>
            GitHub Username *
          </label>
          <input
            value={github}
            onChange={(e) => setGithub(e.target.value)}
            placeholder="e.g. paulatreides"
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

        {/* Email */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 14, color: "#aaa" }}>
            Email *
          </label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
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
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span style={{ fontSize: 14 }}>
            I consent to data processing for project mining *
          </span>

          {github.trim() !== "" && email.trim() !== "" && !consent && (
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
            {isSaving ? "Saving..." : "Fill all required fields"}
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleClose}
              disabled={isSaving}
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
              disabled={!isValid || isSaving}
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