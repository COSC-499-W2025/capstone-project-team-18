import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/apiClient";
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

type PortfolioListItem = {
  id: number;
  title: string;
  creation_time?: string;
};

type ListPortfoliosResponse = {
  portfolios: PortfolioListItem[];
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

  const [portfolios, setPortfolios] = useState<PortfolioListItem[]>([]);
  const [portfoliosLoading, setPortfoliosLoading] = useState(true);
  const [portfoliosError, setPortfoliosError] = useState<string | null>(null);

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

  async function loadPortfolios() {
    try {
      setPortfoliosLoading(true);
      setPortfoliosError(null);
      const res = (await api.getPortfolios()) as ListPortfoliosResponse;
      setPortfolios(Array.isArray(res?.portfolios) ? res.portfolios : []);
    } catch (e: any) {
      setPortfoliosError(e?.message ?? "Failed to load portfolios");
      setPortfolios([]);
    } finally {
      setPortfoliosLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
    loadPortfolios();
  }, []);

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
          Start Mining
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
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
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
                {projects.slice(0, 3).map((project) => (
                  <Link
                    key={project.project_name}
                    to={`/projects/${encodeURIComponent(
                      project.project_name
                    )}`}
                    style={{
                      display: "block",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid #2a2a2a",
                      borderRadius: 12,
                      padding: 14,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>
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
            <div style={{ color: "#999", lineHeight: 1.6 }}>
              View generated resume content, review extracted skills, and inspect
              resume items for peer testing.
            </div>
          </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/resume/1" style={{ color: "#6f7cff" }}>
              Open Resume
            </Link>
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

            {portfoliosLoading && <div>Loading portfolios…</div>}

            {!portfoliosLoading && portfoliosError && (
              <div style={{ color: "#ff8a8a", fontSize: 14 }}>
                Failed to load.
              </div>
            )}

            {!portfoliosLoading && !portfoliosError && portfolios.length === 0 && (
              <div style={{ color: "#999" }}>No portfolios yet.</div>
            )}

            {!portfoliosLoading && !portfoliosError && portfolios.length > 0 && (
              <div style={{ display: "grid", gap: 12 }}>
                {portfolios.slice(0, 3).map((p) => (
                  <Link
                    key={p.id}
                    to={`/portfolios/${p.id}`}
                    style={{
                      display: "block",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid #2a2a2a",
                      borderRadius: 12,
                      padding: 14,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{p.title}</div>
                    <div style={{ fontSize: 12, color: "#999", marginTop: 6 }}>
                      Created: {formatDate(p.creation_time)}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/portfolios" style={{ color: "#6f7cff" }}>
              View all
            </Link>
          </div>
        </section>
      </div>

      <UploadProjectModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
      />
    </div>
  );
}