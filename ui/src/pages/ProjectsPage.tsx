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
    <div style={{ padding: 24, paddingTop: 40 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>Projects</h1>
          <p style={{ marginTop: 8, color: "#666" }}>
            Browse uploaded projects and open a project to view details.
          </p>
        </div>

        <button
          onClick={load}
          disabled={loading}
          style={{ padding: "10px 14px" }}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {loading && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
          }}
        >
          Loading projects...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            border: "1px solid #3a1f1f",
            borderRadius: 16,
            padding: 20,
            background: "#1a1111",
            color: "#ff8a8a",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
            color: "#999",
          }}
        >
          No projects found.
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div
          style={{
            display: "grid",
            gap: 16,
          }}
        >
          {projects.map((p) => (
            <Link
              key={p.project_name}
              to={`/projects/${encodeURIComponent(p.project_name)}`}
              style={{
                display: "block",
                textDecoration: "none",
                color: "inherit",
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                padding: 18,
                background: "#161616",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 20 }}>
                    {p.project_name}
                  </div>
                  <div style={{ fontSize: 13, color: "#999", marginTop: 8 }}>
                    Created: {formatDate(p.created_at)}
                  </div>
                  <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                    Updated: {formatDate(p.last_updated)}
                  </div>
                </div>

                {p.user_config_used != null && (
                  <div
                    style={{
                      fontSize: 12,
                      color: "#ddd",
                      border: "1px solid #2a2a2a",
                      borderRadius: 999,
                      padding: "6px 10px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Config #{p.user_config_used}
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}