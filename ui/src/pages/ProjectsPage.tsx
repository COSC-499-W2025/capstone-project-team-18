import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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
          <div style={{ color: "#999", marginBottom: 16 }}>
            Project analysis in progress...
            </div>
            <ProjectSkeleton count={6} />
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
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: 20,
            alignItems: "stretch",
          }}
        >
          {projects.map((p) => (
            <Link
              key={p.project_name}
              to={`/projects/${encodeURIComponent(p.project_name)}`}
              style={{
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                background: "#161616",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                overflow: "hidden",
                padding: 20,
                textDecoration: "none",
                color: "inherit",
                cursor: "pointer",
                transition: "border-color 0.15s, background 0.15s",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.borderColor = "#6f7cff";
                (e.currentTarget as HTMLElement).style.background = "#1a1a2e";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.borderColor = "#2a2a2a";
                (e.currentTarget as HTMLElement).style.background = "#161616";
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
                <div style={{ fontWeight: 700, fontSize: 20, lineHeight: 1.3, wordBreak: "break-word", flex: 1 }}>
                  {p.project_name}
                </div>

                {p.image_data && (
                  <div style={{ width: 120, height: 80, flexShrink: 0, borderRadius: 8, overflow: "hidden", background: "#0d0d0d" }}>
                    <img
                      src={getImageSrc(p.image_data)}
                      alt={`${p.project_name} thumbnail`}
                      style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                    />
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