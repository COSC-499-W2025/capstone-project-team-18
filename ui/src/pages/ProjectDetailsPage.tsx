import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/apiClient";

type ProjectReport = {
  project_name: string;
  user_config_used?: number | null;
  image_data?: unknown | null;
  created_at: string;
  last_updated: string;
};

function isNotFoundError(msg: string) {
  return msg.includes("API request failed (404)");
}

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function ProjectDetailsPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const projectName = id ?? "";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectReport | null>(null);

  useEffect(() => {
    if (!projectName) {
      navigate("/projects", { replace: true });
      return;
    }

    let alive = true;

    (async () => {
      try {
        setLoading(true);
        setError(null);
        setProject(null);

        const res = (await api.getProject(projectName)) as ProjectReport;
        if (alive) setProject(res);
      } catch (e: any) {
        if (alive) setError(e?.message ?? "Failed to load project");
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [projectName, navigate]);

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      <div style={{ marginBottom: 20 }}>
        <button
          type="button"
          onClick={() => navigate("/projects")}
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            color: "#6f7cff",
            cursor: "pointer",
            fontSize: 16,
          }}
        >
          ← Back to Projects
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
          Loading project details...
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
          {isNotFoundError(error) ? (
            <>
              <strong>Not found:</strong> No project named{" "}
              <code>{projectName}</code>
            </>
          ) : (
            <>
              <strong>Error:</strong> {error}
            </>
          )}
        </div>
      )}

      {!loading && project && (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <div>
              <h1 style={{ margin: 0 }}>{project.project_name}</h1>
              <p style={{ marginTop: 8, color: "#666" }}>
                Review project metadata and mined information.
              </p>
            </div>

            <button
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid #2a2a2a",
                background: "transparent",
                color: "#ddd",
                cursor: "pointer",
              }}
            >
              Delete Project
            </button>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <section
              style={{
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                padding: 18,
                background: "#161616",
              }}
            >
              <div style={{ fontSize: 13, color: "#999", marginBottom: 8 }}>
                Date Created
              </div>
              <div style={{ fontWeight: 600 }}>{formatDate(project.created_at)}</div>
            </section>

            <section
              style={{
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                padding: 18,
                background: "#161616",
              }}
            >
              <div style={{ fontSize: 13, color: "#999", marginBottom: 8 }}>
                Last Updated
              </div>
              <div style={{ fontWeight: 600 }}>{formatDate(project.last_updated)}</div>
            </section>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr",
              gap: 16,
              marginBottom: 24,
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
              <h2 style={{ marginTop: 0 }}>Project Overview</h2>
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                Detailed project content and editable metadata will be connected
                in the next integration pass. For peer testing, this section
                represents where mined project details and user-adjustable
                project information will appear.
              </div>
            </section>

            <section
              style={{
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                padding: 20,
                background: "#161616",
              }}
            >
              <h2 style={{ marginTop: 0 }}>Skills</h2>
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                Skills extracted for this project will appear here once the full
                data mapping is connected.
              </div>
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
            <h2 style={{ marginTop: 0 }}>Raw Project Data</h2>
            <pre
              style={{
                background: "#101010",
                padding: 14,
                borderRadius: 12,
                overflow: "auto",
                margin: 0,
                maxHeight: 360,
                color: "#d8d8d8",
                fontSize: 13,
              }}
            >
              {JSON.stringify(project, null, 2)}
            </pre>
          </section>
        </>
      )}
    </div>
  );
}