import { useState } from "react";

type AddSkillsModalProps = {
  /** Auto-generated skills from the project card — shown as suggestion chips */
  suggestions: string[];
  /** Currently selected skills — shown as tokens when modal opens */
  initialSelected: string[];
  onConfirm: (skills: string[]) => void;
  onClose: () => void;
};

export default function AddSkillsModal({
  suggestions,
  initialSelected,
  onConfirm,
  onClose,
}: AddSkillsModalProps) {
  const [input, setInput] = useState("");
  const [selected, setSelected] = useState<string[]>([...initialSelected]);

  function addSkill(skill: string) {
    const trimmed = skill.trim();
    if (!trimmed || selected.includes(trimmed)) return;
    setSelected((prev) => [...prev, trimmed]);
  }

  function removeSkill(skill: string) {
    setSelected((prev) => prev.filter((s) => s !== skill));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && input.trim()) {
      e.preventDefault();
      addSkill(input);
      setInput("");
    }
  }

  function handleConfirm() {
    const final =
      input.trim() && !selected.includes(input.trim())
        ? [...selected, input.trim()]
        : selected;
    onConfirm(final);
  }

  const availableSuggestions = suggestions.filter((s) => !selected.includes(s));

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1200,
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 480,
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          padding: 24,
          boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Add Skills</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "transparent",
              border: "none",
              color: "#888",
              cursor: "pointer",
              fontSize: 22,
              lineHeight: 1,
              padding: "2px 6px",
              borderRadius: 6,
            }}
          >
            ✕
          </button>
        </div>

        {/* Text input */}
        <input
          type="text"
          placeholder="Enter a skill"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--bg-input)",
            color: "#fff",
            fontSize: 14,
            boxSizing: "border-box",
            outline: "none",
          }}
        />

        {/* Selected tokens */}
        {selected.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              marginTop: 10,
            }}
          >
            {selected.map((skill) => (
              <span
                key={skill}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  fontSize: 12,
                  color: "var(--accent)",
                  border: "1px solid #6f7cff44",
                  borderRadius: 999,
                  padding: "3px 10px",
                  background: "#6f7cff11",
                }}
              >
                {skill}
                <button
                  onClick={() => removeSkill(skill)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#6f7cff99",
                    cursor: "pointer",
                    fontSize: 15,
                    lineHeight: 1,
                    padding: 0,
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Suggestions */}
        {availableSuggestions.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <div
              style={{
                fontSize: 11,
                color: "#666",
                marginBottom: 10,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Skill suggestions
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {availableSuggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => addSkill(s)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    fontSize: 12,
                    color: "#555",
                    border: "1px solid var(--border)",
                    borderRadius: 999,
                    padding: "5px 12px",
                    background: "transparent",
                    cursor: "pointer",
                  }}
                >
                  <span style={{ color: "#777", fontSize: 14, fontWeight: 700 }}>+</span>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 28,
            borderTop: "1px solid var(--border)",
            paddingTop: 18,
          }}
        >
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#aaa",
              cursor: "pointer",
              fontSize: 14,
              padding: "8px 0",
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            style={{
              padding: "9px 20px",
              borderRadius: 8,
              border: "none",
              background: "#2563eb",
              color: "#fff",
              cursor: "pointer",
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            Add Skills
          </button>
        </div>
      </div>
    </div>
  );
}
