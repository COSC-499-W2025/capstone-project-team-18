import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/apiClient";

type ResumeItemResponse = {
  id?: number | null;
  resume_id?: number | null;
  project_name?: string | null;
  title: string;
  frameworks: string[];
  bullet_points: string[];
  start_date?: string | null;
  end_date?: string | null;
};

type ResumeResponse = {
  id?: number | null;
  email?: string | null;
  github?: string | null;
  skills: string[];
  items: ResumeItemResponse[];
  created_at?: string | null;
  last_updated?: string | null;
};

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function ResumePage() {
  const { id } = useParams();
  const resumeId = id ?? "1";

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [resume, setResume] = useState<ResumeResponse | null>(null);

  useEffect(() => {
    let alive = true;

    async function loadResume() {
      try {
        setLoading(true);
        setError(null);
        setSuccess(null);

        const res = (await api.getResume(resumeId)) as ResumeResponse;

        if (!alive) return;
        setResume(res);
      } catch (e: any) {
        if (!alive) return;

        // Frontend-only placeholder data for now
        setResume({
          id: Number(resumeId) || 1,
          email: "student@example.com",
          github: "thndlovu",
          skills: ["Python", "React", "TypeScript", "FastAPI", "SQLModel"],
          created_at: new Date().toISOString(),
          last_updated: new Date().toISOString(),
          items: [
            {
              id: 1,
              resume_id: Number(resumeId) || 1,
              project_name: "Digital Artifact Miner",
              title: "Digital Artifact Miner",
              frameworks: ["React", "TypeScript", "FastAPI"],
              bullet_points: [
                "Built frontend workflows for dashboard navigation, upload flows, and settings management.",
                "Implemented backend-ready UI components for peer testing and future endpoint integration.",
              ],
              start_date: "2025-09-01",
              end_date: "2026-03-01",
            },
            {
              id: 2,
              resume_id: Number(resumeId) || 1,
              project_name: "ESM Strategists Website",
              title: "ESM Strategists Website",
              frameworks: ["HTML", "CSS", "JavaScript"],
              bullet_points: [
                "Designed and developed a polished business website with responsive layouts and reusable styling patterns.",
                "Improved visual hierarchy and maintainability to support future content expansion.",
              ],
              start_date: "2025-06-01",
              end_date: "2025-08-01",
            },
          ],
        });

        setError(null);
      } finally {
        if (alive) setLoading(false);
      }
    }

    loadResume();

    return () => {
      alive = false;
    };
  }, [resumeId]);

  async function handleGenerateResume() {
    try {
      setGenerating(true);
      setError(null);
      setSuccess(null);

      // Frontend-only placeholder for now
      await new Promise((resolve) => setTimeout(resolve, 800));

      setSuccess("Generate Resume frontend flow complete. Backend hookup pending.");
    } catch (e: any) {
      setError(e?.message ?? "Failed to generate resume.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSaveChanges() {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Frontend-only placeholder for now
      await new Promise((resolve) => setTimeout(resolve, 700));

      setSuccess("Resume changes saved in frontend state. Backend hookup pending.");
    } catch (e: any) {
      setError(e?.message ?? "Failed to save resume.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      {loading && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
          }}
        >
          Loading resume...
        </div>
      )}

      {!loading && resume && (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <h1 style={{ margin: 0 }}>Resume</h1>

            <div style={{ display: "flex", gap: 12 }}>
              <button
                type="button"
                onClick={handleGenerateResume}
                disabled={generating || saving}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid #2a2a2a",
                  background: "#1a1a1a",
                  color: "#ddd",
                  cursor: generating || saving ? "not-allowed" : "pointer",
                  opacity: generating || saving ? 0.7 : 1,
                }}
              >
                {generating ? "Generating..." : "Generate Resume"}
              </button>

              <button
                type="button"
                onClick={handleSaveChanges}
                disabled={saving || generating}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid #2a2a2a",
                  background: "#1a1a1a",
                  color: "#ddd",
                  cursor: saving || generating ? "not-allowed" : "pointer",
                  opacity: saving || generating ? 0.7 : 1,
                }}
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>

          {error && (
            <div
              style={{
                border: "1px solid #3a1f1f",
                borderRadius: 12,
                padding: 14,
                background: "#1a1111",
                color: "#ff8a8a",
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          {success && (
            <div
              style={{
                border: "1px solid #22462b",
                borderRadius: 12,
                padding: 14,
                background: "#102015",
                color: "#8ad6a2",
                marginBottom: 16,
              }}
            >
              {success}
            </div>
          )}

          <section
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Resume Items</h2>

            {!resume.items || resume.items.length === 0 ? (
              <div style={{ color: "#999" }}>No resume items found.</div>
            ) : (
              <div style={{ display: "grid", gap: 16 }}>
                {resume.items.map((item, index) => (
                  <div
                    key={`${item.title}-${index}`}
                    style={{
                      border: "1px solid #2a2a2a",
                      borderRadius: 14,
                      padding: 16,
                      background: "#101010",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        gap: 12,
                        marginBottom: 10,
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 18 }}>
                          {item.title}
                        </div>

                        <div
                          style={{
                            fontSize: 13,
                            color: "#999",
                            marginTop: 4,
                          }}
                        >
                          {formatDate(item.start_date)} – {formatDate(item.end_date)}
                        </div>

                        {item.project_name && (
                          <div
                            style={{
                              fontSize: 13,
                              color: "#999",
                              marginTop: 4,
                            }}
                          >
                            Source Project: {item.project_name}
                          </div>
                        )}
                      </div>

                      <button
                        type="button"
                        style={{
                          padding: "8px 12px",
                          borderRadius: 10,
                          border: "1px solid #2a2a2a",
                          background: "transparent",
                          color: "#ddd",
                          cursor: "pointer",
                        }}
                      >
                        Edit
                      </button>
                    </div>

                    {item.bullet_points && item.bullet_points.length > 0 && (
                      <ul style={{ margin: "0 0 12px 18px", color: "#ddd" }}>
                        {item.bullet_points.map((bullet, bulletIndex) => (
                          <li key={bulletIndex} style={{ marginBottom: 6 }}>
                            {bullet}
                          </li>
                        ))}
                      </ul>
                    )}

                    {item.frameworks && item.frameworks.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {item.frameworks.map((framework, fwIndex) => (
                          <div
                            key={`${framework}-${fwIndex}`}
                            style={{
                              padding: "6px 10px",
                              borderRadius: 999,
                              border: "1px solid #2a2a2a",
                              background: "#161616",
                              fontSize: 12,
                              color: "#ddd",
                            }}
                          >
                            {framework}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}