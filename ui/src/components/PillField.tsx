import React from "react";

// Shared label style used across card/form editors
export const sectionLabel: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text-muted)",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  display: "block",
  marginBottom: 8,
};

export type PillFieldProps = {
  label: string;
  pills: string[];
  inputValue: string;
  pillColor: string;
  borderColor: string;
  bgColor: string;
  placeholder: string;
  disabled?: boolean;
  onRemove: (value: string) => void;
  onInputChange: (value: string) => void;
  onAdd: (value: string) => void;
};

export default function PillField({
  label,
  pills,
  inputValue,
  pillColor,
  borderColor,
  bgColor,
  placeholder,
  disabled,
  onRemove,
  onInputChange,
  onAdd,
}: PillFieldProps) {
  return (
    <div>
      <div style={sectionLabel}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
        {pills.map((p) => (
          <span
            key={p}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: 12,
              color: pillColor,
              border: `1px solid ${borderColor}`,
              borderRadius: 999,
              padding: "3px 10px",
              background: bgColor,
            }}
          >
            {p}
            <button
              onClick={() => onRemove(p)}
              disabled={disabled}
              style={{
                background: "transparent",
                border: "none",
                color: `${pillColor}99`,
                cursor: disabled ? "not-allowed" : "pointer",
                fontSize: 14,
                lineHeight: 1,
                padding: 0,
              }}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onAdd(inputValue.trim());
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          style={{
            flex: 1,
            padding: "6px 10px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--bg-input)",
            color: "var(--text-primary)",
            fontSize: 12,
            outline: "none",
            opacity: disabled ? 0.6 : 1,
          }}
        />
        <button
          onClick={() => onAdd(inputValue.trim())}
          disabled={disabled}
          style={{
            padding: "6px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "transparent",
            color: "var(--text-muted)",
            cursor: disabled ? "not-allowed" : "pointer",
            fontSize: 12,
            opacity: disabled ? 0.6 : 1,
          }}
        >
          + Add
        </button>
      </div>
    </div>
  );
}
