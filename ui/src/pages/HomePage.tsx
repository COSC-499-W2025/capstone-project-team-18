import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  getLatestResumeId,
  type ResumeResponse,
} from "../api/apiClient";
import UploadProjectModal from "../components/update/modal/UploadProjectModal";

type ProjectListItem = {
  project_name: string;
  created_at?: string;
  last_updated?: string;
  user_config_used?: number | null;
};

type ListProjectsResponse = {
  projects: ProjectListItem[];
};

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function HomePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [latestResumeId, setLatestResumeId] = useState<number | null>(null);
  const [latestResume, setLatestResume] = useState<ResumeResponse | null>(null);
  const [hoveredProjectName, setHoveredProjectName] = useState<string | null>(null);

  async function loadProjects() {
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
    loadProjects();
    loadLatestResume();
  }, []);

  async function loadLatestResume() {
    const resumeId = getLatestResumeId();
    setLatestResumeId(resumeId);

    if (!resumeId) {
      setLatestResume(null);
      return;
    }

    try {
      const resume = await api.getResume(resumeId);
      setLatestResume(resume);
    } catch {
      setLatestResume(null);
    }
  }

  async function handleUploadSuccess() {
    setShowUploadModal(false);
    await loadProjects();
  }

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>Dashboard</h1>
          <p style={{ marginTop: 8, color: "#666" }}>
            Manage projects, resumes, portfolios, and settings.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          style={{ padding: "10px 14px" }}
        >
          Upload Project
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ marginBottom: 16, color: "crimson" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.15fr 0.85fr",
          gap: 20,
          alignItems: "stretch",
        }}
      >
        {/* Projects */}
        <section
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
            minHeight: 220,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h2 style={{ marginTop: 0 }}>Projects</h2>

            {loading && <div>Loading projects…</div>}

            {!loading && !error && projects.length === 0 && (
              <div>No projects found.</div>
            )}

            {!loading && !error && projects.length > 0 && (
              <div style={{ display: "grid", gap: 12 }}>
                {projects.map((project) => (
                  <Link
                    key={project.project_name}
                    to={`/projects/${encodeURIComponent(
                      project.project_name
                    )}`}
                    onMouseEnter={() => setHoveredProjectName(project.project_name)}
                    onMouseLeave={() => setHoveredProjectName(null)}
                    style={{
                      display: "block",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid #2a2a2a",
                      borderRadius: 12,
                      padding: 14,
                      background:
                        hoveredProjectName === project.project_name
                          ? "#151515"
                          : "#101010",
                      transition: "background 0.2s ease, transform 0.2s ease",
                      transform:
                        hoveredProjectName === project.project_name
                          ? "translateY(-1px)"
                          : "translateY(0)",
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#ddd" }}>
                      {project.project_name}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: "#999",
                        marginTop: 6,
                      }}
                    >
                      Created: {formatDate(project.created_at)}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/projects" style={{ color: "#6f7cff" }}>
              View all
            </Link>
          </div>
        </section>

        <div
          style={{
            display: "grid",
            gridTemplateRows: "1fr 1fr",
            gap: 20,
          }}
        >
          {/* Resume */}
          <section
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
              minHeight: 220,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <h2 style={{ marginTop: 0 }}>Resume</h2>
              <div style={{ color: "#999", lineHeight: 1.6, marginBottom: 16 }}>
                View generated resume content, review extracted skills, and
                review resume items.
              </div>

              {latestResume?.items && latestResume.items.length > 0 ? (
                <div style={{ display: "grid", gap: 10 }}>
                  {latestResume.items.map((item, index) => (
                    <div
                      key={`${item.title}-${index}`}
                      style={{
                        border: "1px solid #2a2a2a",
                        borderRadius: 10,
                        padding: "10px 12px",
                        background: "#101010",
                        color: "#ddd",
                      }}
                    >
                      {item.title}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "#999" }}>No generated resume items yet.</div>
              )}
            </div>

            <div style={{ marginTop: 20 }}>
              {latestResumeId ? (
                <Link
                  to={`/resume/${latestResumeId}`}
                  style={{ color: "#6f7cff" }}
                >
                  Open Resume
                </Link>
              ) : (
                <span style={{ color: "#999" }}>
                  Generate a resume to view it here.
                </span>
              )}
            </div>
          </section>

          {/* Portfolios */}
          <section
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
              minHeight: 220,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <h2 style={{ marginTop: 0 }}>Portfolios</h2>
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                Portfolio support coming soon.
              </div>
            </div>
          </section>
          </div>
      </div>

      <UploadProjectModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}