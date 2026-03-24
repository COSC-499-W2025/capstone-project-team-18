import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/apiClient";

type ProjectListItem = {
  project_name: string;
  created_at?: string;
  last_updated?: string;
  user_config_used?: number | null;
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

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function formatUserConfigLabel(value?: number | null) {
  if (value === null || value === undefined) return "No config";
  return `Config #${value}`;
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
            borderRadius: 20,
            padding: 28,
            background: "#161616",
            color: "#999",
          }}
        >
          <div style={{ fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 8 }}>
            No projects found
          </div>
          <div style={{ lineHeight: 1.6 }}>
            Upload and mine a project from the dashboard to see it appear here.
          </div>
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            gap: 20,
            alignItems: "stretch",
          }}
        >
          {projects.map((p) => (
            <section
              key={p.project_name}
              style={{
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                background: "#161616",
                minHeight: 220,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                overflow: "hidden",
              }}
            >
              {p.image_data && (
                <div style={{ width: "100%", height: 160, overflow: "hidden", flexShrink: 0, background: "#0d0d0d", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <img
                    src={getImageSrc(p.image_data)}
                    alt={`${p.project_name} thumbnail`}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "contain",
                      display: "block",
                    }}
                  />
                </div>
              )}

              <div style={{ padding: 20, flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: 12,
                      marginBottom: 16,
                    }}
                  >
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: 20,
                        lineHeight: 1.3,
                        wordBreak: "break-word",
                      }}
                    >
                      {p.project_name}
                    </div>

                    {p.user_config_used !== null && p.user_config_used !== undefined && (
                      <div
                        style={{
                          padding: "6px 10px",
                          borderRadius: 999,
                          border: "1px solid #2a2a2a",
                          background: "#101010",
                          fontSize: 12,
                          color: "#bbb",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {formatUserConfigLabel(p.user_config_used)}
                      </div>
                    )}
                  </div>

                  <Link
                    to={`/projects/${encodeURIComponent(p.project_name)}`}
                    style={{
                      display: "block",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid #2a2a2a",
                      borderRadius: 12,
                      padding: 14,
                    }}
                  >
                    <div style={{ color: "#999", fontSize: 14, lineHeight: 1.7 }}>
                      <div>Created: {formatDate(p.created_at)}</div>
                      <div>Updated: {formatDate(p.last_updated)}</div>
                    </div>
                  </Link>
                </div>

                <div style={{ marginTop: 20 }}>
                  <Link
                    to={`/projects/${encodeURIComponent(p.project_name)}`}
                    style={{ color: "#6f7cff", textDecoration: "none", fontSize: 14 }}
                  >
                    View →
                  </Link>
                </div>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}