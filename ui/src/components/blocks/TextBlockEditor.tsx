type TextBlockEditorProps = {
  draft: string;
  saving: boolean;
  error: string | null;
  onChange: (value: string) => void;
  onSave: () => void;
};

export default function TextBlockEditor({
  draft,
  saving,
  error,
  onChange,
  onSave,
}: TextBlockEditorProps) {
  return (
    <div>
      <textarea
        value={draft}
        onChange={(e) => onChange(e.target.value)}
        rows={4}
        style={{
          width: "100%",
          padding: "8px 10px",
          borderRadius: 8,
          border: "1px solid #2a2a2a",
          background: "#0d0d0d",
          color: "#ddd",
          fontSize: 13,
          resize: "vertical",
          boxSizing: "border-box",
          fontFamily: "inherit",
          lineHeight: 1.6,
        }}
      />

      {error && (
        <div style={{ color: "#ff8a8a", fontSize: 12, marginTop: 6 }}>
          {error}
        </div>
      )}

      <button
        onClick={onSave}
        disabled={saving}
        style={{
          marginTop: 10,
          padding: "7px 12px",
          borderRadius: 8,
          border: "none",
          background: saving ? "#202020" : "#2b2b2b",
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
