import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/apiClient";
import ProjectSkeleton from "@/components/ProjectSkeleton";

type ProjectListItem = {
  project_name: string;
  image_data?: string | null;
};

function getImageSrc(base64: string): string {
  if (base64.startsWith("/9j/")) return `data:image/jpeg;base64,${base64}`;
  if (base64.startsWith("iVBOR")) return `data:image/png;base64,${base64}`;
  if (base64.startsWith("R0lG")) return `data:image/gif;base64,${base64}`;
  if (base64.startsWith("UklG")) return `data:image/webp;base64,${base64}`;
  return `data:image/jpeg;base64,${base64}`;
}

type ListProjectsResponse = {
  projects: ProjectListItem[];
};


const ANALYSIS_KEY = "project_analysis_in_progress";
const COUNT_KEY = "project_count_before_upload";

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [isAnalysisInProgress, setIsAnalysisInProgress] = useState(
    () => localStorage.getItem(ANALYSIS_KEY) === "true"
  );
  const [projectCountBeforeUpload] = useState(
    () => parseInt(localStorage.getItem(COUNT_KEY) ?? "0", 10)
  );

  async function load() {
    try {
      setLoading(true);
      setError(null);

      const res = (await api.getProjects()) as ListProjectsResponse;
      setProjects(Array.isArray(res?.projects) ? res.projects : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load projects");
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!isAnalysisInProgress) return;

    const interval = setInterval(async () => {
      try {
        const res = (await api.getProjects()) as ListProjectsResponse;
        const updated = Array.isArray(res?.projects) ? res.projects : [];
        setProjects(updated);
        if (updated.length > projectCountBeforeUpload) {
          setIsAnalysisInProgress(false);
          localStorage.removeItem(ANALYSIS_KEY);
          localStorage.removeItem(COUNT_KEY);
        }
      } catch {
        setIsAnalysisInProgress(false);
        localStorage.removeItem(ANALYSIS_KEY);
        localStorage.removeItem(COUNT_KEY);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [isAnalysisInProgress, projectCountBeforeUpload]);

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
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>Projects</h1>
          <p style={{ marginTop: 6, color: "var(--text-secondary)", margin: "6px 0 0" }}>
            Browse uploaded projects and open a project to view details.
          </p>
        </div>

        <button
          onClick={() => navigate("/", { state: { openUploadModal: true } })}
          style={{
            padding: "10px 18px",
            borderRadius: 10,
            border: "none",
            background: "var(--btn-primary)",
            color: "#fff",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Upload Project
        </button>
      </div>

      {isAnalysisInProgress && (
        <div style={{ color: "var(--text-muted)", marginBottom: 16, fontSize: 14 }}>
          Project analysis in progress...
        </div>
      )}

      {loading && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 20,
            background: "var(--bg-surface)",
          }}
        >
          <div style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 16 }}>
            Loading projects...
          </div>
          <ProjectSkeleton count={6} />
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

      {!loading && !error && projects.length === 0 && !isAnalysisInProgress && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 20,
            background: "var(--bg-surface)",
            color: "var(--text-muted)",
          }}
        >
          No projects yet. Click "Upload Project" to get started.
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div style={{ display: "grid", gap: 12 }}>
          {projects.map((p) => (
            <Link
              key={p.project_name}
              to={`/projects/${encodeURIComponent(p.project_name)}`}
              state={{ from: "/projects" }}
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
                  alignItems: "center",
                  gap: 16,
                }}
              >
                <div style={{ fontWeight: 700, fontSize: 17, wordBreak: "break-word", flex: 1 }}>
                  {p.project_name}
                </div>

                {p.image_data ? (
                  <div style={{ width: 120, height: 80, flexShrink: 0, borderRadius: 8, overflow: "hidden", background: "#f0f0f0" }}>
                    <img
                      src={getImageSrc(p.image_data)}
                      alt={`${p.project_name} thumbnail`}
                      style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                    />
                  </div>
                ) : (
                  <div style={{ color: "#444", fontSize: 18, flexShrink: 0 }}>→</div>
                )}
              </div>
            </Link>
          ))}
          {isAnalysisInProgress && <ProjectSkeleton count={3} />}
        </div>
      )}

      {!loading && !error && projects.length === 0 && isAnalysisInProgress && (
        <ProjectSkeleton count={3} />
      )}
    </div>
  );
}
