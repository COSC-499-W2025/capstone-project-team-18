type TextListBlockEditorProps = {
  draft: string[];
  saving: boolean;
  error: string | null;
  onChange: (items: string[]) => void;
  onSave: () => void;
};

export default function TextListBlockEditor({
  draft,
  saving,
  error,
  onChange,
  onSave,
}: TextListBlockEditorProps) {
  return (
    <div>
      {draft.map((item, index) => (
        <div
          key={index}
          style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}
        >
          <input
            value={item}
            onChange={(e) => {
              const updated = [...draft];
              updated[index] = e.target.value;
              onChange(updated);
            }}
            style={{
              flex: 1,
              padding: "7px 10px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "#f0f0f0",
              color: "#333",
              fontSize: 13,
              boxSizing: "border-box",
            }}
          />
          <button
            onClick={() => onChange(draft.filter((_, i) => i !== index))}
            disabled={saving}
            style={{
              padding: "6px 10px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "transparent",
              color: "var(--danger-text)",
              cursor: saving ? "not-allowed" : "pointer",
              fontSize: 12,
              whiteSpace: "nowrap",
            }}
          >
            Remove
          </button>
        </div>
      ))}

      <button
        onClick={() => onChange([...draft, ""])}
        disabled={saving}
        style={{
          padding: "6px 12px",
          borderRadius: 8,
          border: "1px solid var(--border)",
          background: "transparent",
          color: "var(--accent)",
          cursor: saving ? "not-allowed" : "pointer",
          fontSize: 12,
          marginBottom: 10,
          display: "block",
        }}
      >
        + Add Item
      </button>

      {error && (
        <div style={{ color: "var(--danger-text)", fontSize: 12, marginBottom: 6 }}>
          {error}
        </div>
      )}

      <button
        onClick={onSave}
        disabled={saving}
        style={{
          padding: "7px 12px",
          borderRadius: 8,
          border: "none",
          background: saving ? "var(--bg-surface-deep)" : "var(--accent)",
          color: "#fff",
          cursor: saving ? "not-allowed" : "pointer",
          opacity: saving ? 0.6 : 1,
          fontSize: 12,
        }}
      >
        {saving ? "Saving..." : "Save Block"}
      </button>
    </div>
  );
}
