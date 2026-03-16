import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/apiClient";

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
  }, []);

  return (
    <div style={{ padding: 24 }}>
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

        <div style={{ display: "flex", gap: 12 }}>
          <button style={{ padding: "10px 14px" }}>Settings</button>
          <button style={{ padding: "10px 14px" }}>Start Mining</button>
        </div>
      </div>

      {error && (
        <div style={{ marginBottom: 16, color: "crimson" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: 20,
          marginBottom: 20,
        }}
      >
        <section
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Projects</h2>
            <Link to="/projects">View all</Link>
          </div>

          {loading && <div>Loading projects…</div>}

          {!loading && !error && projects.length === 0 && <div>No projects found.</div>}

          {!loading && !error && projects.length > 0 && (
            <div style={{ display: "grid", gap: 12 }}>
              {projects.slice(0, 4).map((project) => (
                <Link
                  key={project.project_name}
                  to={`/projects/${encodeURIComponent(project.project_name)}`}
                  style={{
                    display: "block",
                    textDecoration: "none",
                    color: "inherit",
                    border: "1px solid #2a2a2a",
                    borderRadius: 12,
                    padding: 14,
                  }}
                >
                  <div style={{ fontWeight: 600 }}>{project.project_name}</div>
                  <div style={{ fontSize: 12, color: "#999", marginTop: 6 }}>
                    Created: {formatDate(project.created_at)}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
          }}
        >
          <h2 style={{ marginTop: 0 }}>Resumes</h2>
          <div style={{ color: "#999" }}>Resume view coming next.</div>
        </section>
      </div>

      <section
        style={{
          border: "1px solid #2a2a2a",
          borderRadius: 16,
          padding: 20,
          background: "#161616",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Portfolios</h2>
        <div style={{ color: "#999" }}>Portfolio support coming soon.</div>
      </section>
    </div>
  );
}