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

export default function ProjectsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);

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

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h1 style={{ marginTop: 0, marginBottom: 0 }}>Projects</h1>
        <button onClick={load} disabled={loading} style={{ padding: "6px 10px" }}>
          Refresh
        </button>
      </div>

      <p style={{ marginTop: 8, color: "#666" }}>
        Data from <code>GET /projects</code>. Click a project to view details.
      </p>

      {loading && <div>Loading projects…</div>}

      {!loading && error && (
        <div style={{ color: "crimson" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div>No projects found.</div>
      )}

      {!loading && !error && projects.length > 0 && (
        <ul style={{ paddingLeft: 18 }}>
          {projects.map((p) => (
            <li key={p.project_name} style={{ marginBottom: 10 }}>
              <div>
                <Link
                  to={`/projects/${encodeURIComponent(p.project_name)}`}
                  style={{ fontWeight: 600 }}
                >
                  {p.project_name}
                </Link>
              </div>
              <div style={{ fontSize: 12, color: "#666" }}>
                Created: {formatDate(p.created_at)} · Updated:{" "}
                {formatDate(p.last_updated)}
                {p.user_config_used != null && (
                  <> · User config: {p.user_config_used}</>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}