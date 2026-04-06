import { Link } from "react-router-dom";

/**
 * TourResumePage — a static mock resume used exclusively by the walkthrough
 * tour when the user has no real resumes yet. It replicates the real ResumePage
 * layout exactly (same structure, same button styles, same CSS variables) so
 * tour steps 10 and 11 can spotlight the export buttons in a familiar context.
 * The export buttons look and feel real but are no-ops during the tour.
 */
const SECTION_LABEL: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "var(--text-muted)",
  marginBottom: 12,
};

const CARD: React.CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 14,
  padding: "16px 20px",
  background: "var(--bg-surface)",
  marginBottom: 14,
};

const ROW: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "baseline",
  gap: 8,
  marginBottom: 4,
};

export default function TourResumePage() {
  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      {/* Back link */}
      <Link to="/resumes" style={{ color: "var(--accent)", textDecoration: "none", fontSize: 14 }}>
        ← Back to Resumes
      </Link>

      {/* Title row + action bar */}
      <div
        style={{
          marginTop: 20,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
          marginBottom: 24,
        }}
      >
        {/* Title */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h1 style={{ margin: 0, fontSize: 28 }}>Example Resume</h1>
            <button
              disabled
              style={{
                padding: "4px 8px",
                borderRadius: 8,
                border: "1px solid var(--btn-primary)",
                background: "transparent",
                color: "var(--btn-primary)",
                cursor: "not-allowed",
                fontSize: 14,
                fontWeight: 500,
                opacity: 0.5,
              }}
            >
              Edit
            </button>
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            Created {new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}
          </div>
        </div>

        {/* Action bar */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            disabled
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "none",
              background: "var(--btn-primary)",
              color: "#fff",
              fontWeight: 600,
              cursor: "not-allowed",
              fontSize: 14,
              opacity: 0.5,
            }}
          >
            Save
          </button>

          <button
            data-tour="export-pdf-btn"
            disabled
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--btn-primary)",
              borderRadius: 10,
              color: "var(--btn-primary)",
              fontWeight: 500,
              cursor: "not-allowed",
              fontSize: 14,
            }}
          >
            Export PDF
          </button>

          <button
            data-tour="export-docx-btn"
            disabled
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--btn-primary)",
              borderRadius: 10,
              color: "var(--btn-primary)",
              fontWeight: 500,
              cursor: "not-allowed",
              fontSize: 14,
            }}
          >
            Export Word
          </button>

          <button
            disabled
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--btn-primary)",
              borderRadius: 10,
              color: "var(--btn-primary)",
              fontWeight: 500,
              cursor: "not-allowed",
              fontSize: 14,
              opacity: 0.5,
            }}
          >
            Refresh
          </button>

          <button
            disabled
            style={{
              padding: "10px 14px",
              background: "#dc2626",
              border: "none",
              borderRadius: 10,
              color: "#fff",
              fontWeight: 600,
              cursor: "not-allowed",
              fontSize: 14,
              opacity: 0.5,
            }}
          >
            Delete
          </button>
        </div>
      </div>

      {/* HEADER */}
      <div style={CARD}>
        <span style={SECTION_LABEL}>Header</span>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ display: "grid", gap: 6 }}>
            {[
              ["Name", "Paul Atreides"],
              ["Location", "Caladan"],
              ["Email", "patreides@example.com"],
              ["LinkedIn", "linkedin.com/in/paulatreides"],
              ["GitHub", "github.com/paulatreides"],
            ].map(([label, value]) => (
              <div key={label} style={{ fontSize: 14 }}>
                <span style={{ color: "var(--text-muted)", marginRight: 8 }}>{label}</span>
                <span style={{ color: "var(--text-primary)" }}>{value}</span>
              </div>
            ))}
          </div>
          <button disabled style={editBtnStyle}>Edit</button>
        </div>
      </div>

      {/* EDUCATION */}
      <div style={CARD}>
        <span style={SECTION_LABEL}>Education</span>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={ROW}>
              <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
                BSc Computer Science, University of British Columbia
              </span>
              <span style={{ fontSize: 13, color: "var(--text-muted)", whiteSpace: "nowrap" }}>2020 – 2024</span>
            </div>
          </div>
          <button disabled style={editBtnStyle}>Edit</button>
        </div>
      </div>

      {/* AWARDS */}
      <div style={CARD}>
        <span style={SECTION_LABEL}>Awards</span>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>
            Dean's List 2023
          </div>
          <button disabled style={editBtnStyle}>Edit</button>
        </div>
      </div>

      {/* SKILLS */}
      <div style={CARD}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <span style={SECTION_LABEL}>Skills</span>
          <button disabled style={{ ...editBtnStyle, marginBottom: 12 }}>Edit Skills</button>
        </div>
        {[
          { level: "Expert", skills: ["Python", "React", "TypeScript"] },
          { level: "Intermediate", skills: ["Docker", "PostgreSQL", "Git"] },
          { level: "Exposure", skills: ["Kubernetes", "Spice Collection"] },
        ].map(({ level, skills }) => (
          <div key={level} style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)", minWidth: 90 }}>{level}</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {skills.map((s) => (
                <span
                  key={s}
                  style={{
                    fontSize: 13,
                    padding: "2px 10px",
                    borderRadius: 99,
                    border: "1px solid var(--border)",
                    background: "var(--bg-surface-deep)",
                    color: "var(--text-primary)",
                  }}
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* PROJECTS */}
      <div style={CARD}>
        <span style={SECTION_LABEL}>Projects</span>
        <div style={{ display: "grid", gap: 14 }}>
          {[
            {
              title: "Digital Artifact Miner",
              dates: "January 2025 – April 2025",
              tech: ["React", "TypeScript", "FastAPI", "PostgreSQL"],
              bullets: [
                "Built a full-stack application that analyzes coding projects for skills, technologies, and contributions.",
                "Integrated AI-assisted summaries and GitHub contribution parsing.",
                "Implemented PDF and Word resume export with dynamic formatting.",
              ],
            },
          ].map((proj) => (
            <div
              key={proj.title}
              style={{
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "14px 16px",
                background: "var(--bg-surface-deep)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 2 }}>
                    {proj.title}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{proj.dates}</div>
                </div>
                <button disabled style={editBtnStyle}>Edit</button>
              </div>
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)" }}>
                  Frameworks &amp; Technologies
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                  {proj.tech.map((t) => (
                    <span
                      key={t}
                      style={{
                        fontSize: 12,
                        padding: "2px 8px",
                        borderRadius: 99,
                        border: "1px solid var(--border)",
                        background: "var(--bg-surface)",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                {proj.bullets.map((b) => (
                  <li key={b} style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.65, marginBottom: 4 }}>
                    {b}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const editBtnStyle: React.CSSProperties = {
  padding: "4px 10px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "transparent",
  color: "var(--text-secondary)",
  cursor: "not-allowed",
  fontSize: 13,
  opacity: 0.5,
  flexShrink: 0,
};
