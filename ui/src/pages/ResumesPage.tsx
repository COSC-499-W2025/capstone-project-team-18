import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  api,
  type ResumeListItem,
  type ResumeListResponse,
} from "../api/apiClient";
import CreateResumeModal from "../components/update/modal/CreateResumeModal";

function formatRelativeDate(value?: string | null) {
  if (!value) return "—";
  // Treat naive datetime strings (no timezone suffix) as UTC, since the
  // backend stores UTC datetimes without a 'Z' designator.
  const normalized = /[Zz]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return value;

  const now = Date.now();
  const diff = now - d.getTime();
  const minutes = Math.floor(diff / 60_000);
  const hours = Math.floor(diff / 3_600_000);
  const days = Math.floor(diff / 86_400_000);

  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function ResumesPage() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const res = (await api.getResumes()) as ResumeListResponse;
      setResumes(Array.isArray(res?.resumes) ? res.resumes : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load resumes");
      setResumes([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleCreated(newId: number) {
    setShowCreateModal(false);
    navigate(`/resume/${newId}`);
  }


  return (
    <div style={{ padding: 24, paddingTop: 40, maxWidth: 800, margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 28,
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>Resumes</h1>
          <p style={{ marginTop: 6, color: "var(--text-secondary)", margin: "6px 0 0" }}>
            Create and manage different resume versions tailored for each application.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          style={{
            padding: "10px 18px",
            borderRadius: 10,
            border: "none",
            background: "var(--accent)",
            color: "#fff",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Create Resume
        </button>
      </div>

      <CreateResumeModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={handleCreated}
      />

      {loading && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 20,
            background: "var(--bg-surface)",
            color: "var(--text-secondary)",
            fontSize: 14,
          }}
        >
          Loading resumes...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            border: "1px solid var(--danger-bg-strong)",
            borderRadius: 14,
            padding: 20,
            background: "var(--danger-bg)",
            color: "var(--danger-text)",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && resumes.length === 0 && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 20,
            background: "var(--bg-surface)",
            color: "var(--text-muted)",
          }}
        >
          No resumes yet. Click "Create Resume" to get started.
        </div>
      )}

      {!loading && !error && resumes.length > 0 && (
        <div style={{ display: "grid", gap: 12 }}>
          {resumes.map((resume) => (
            <Link
              key={resume.id}
              to={`/resume/${resume.id}`}
              state={{ from: "/resumes" }}
              style={{
                display: "block",
                textDecoration: "none",
                color: "inherit",
                border: "1px solid var(--border)",
                borderRadius: 14,
                padding: "18px 20px",
                background: "var(--bg-surface)",
                transition: "border-color 0.15s ease, background 0.15s ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--hover-border)";
                (e.currentTarget as HTMLElement).style.background = "var(--hover-bg)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                (e.currentTarget as HTMLElement).style.background = "var(--bg-surface)";
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 16,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Title */}
                  <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 10 }}>
                    {resume.title || `Resume #${resume.id}`}
                  </div>

                  {/* Project pills */}
                  {resume.project_names && resume.project_names.length > 0 ? (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                      {resume.project_names.map((name) => (
                        <span
                          key={name}
                          style={{
                            padding: "3px 10px",
                            borderRadius: 999,
                            border: "1px solid var(--border)",
                            background: "var(--bg-surface-deep)",
                            fontSize: 12,
                            color: "var(--text-muted)",
                          }}
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 10 }}>
                      No projects
                    </div>
                  )}

                  {/* Last updated */}
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Updated {formatRelativeDate(resume.last_updated)}
                  </div>
                </div>

                {/* Arrow */}
                <div style={{ color: "#444", fontSize: 18, flexShrink: 0, marginTop: 2 }}>
                  →
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
