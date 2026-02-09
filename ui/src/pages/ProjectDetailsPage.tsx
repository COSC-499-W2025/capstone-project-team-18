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

export default function ProjectDetailsPage() {
  const navigate = useNavigate();
  const { id } = useParams(); 
  const projectName = id ? decodeURIComponent(id) : "";

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
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 12 }}>
        <button
          type="button"
          onClick={() => navigate("/projects")}
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            color: "#6f7cff",
            cursor: "pointer",
            fontSize: 18,
          }}
        >
          ← Back to Projects
        </button>
      </div>

      <h1 style={{ marginTop: 0 }}>Project Details</h1>
      <p style={{ color: "#666", marginTop: 8 }}>
        Endpoint: <code>GET /projects/{`{project_name}`}</code>
      </p>

      {loading && <div>Loading…</div>}

      {!loading && error && (
        <div style={{ color: "crimson" }}>
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
        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 10 }}>
            <div>
              <strong>Name:</strong> {project.project_name}
            </div>
            <div>
              <strong>Created:</strong> {project.created_at}
            </div>
            <div>
              <strong>Updated:</strong> {project.last_updated}
            </div>
            {project.user_config_used != null && (
              <div>
                <strong>User config used:</strong>{" "}
                {project.user_config_used}
              </div>
            )}
          </div>

          <pre
            style={{
              background: "#f6f6f6",
              padding: 14,
              borderRadius: 10,
              overflow: "auto",
              margin: 0,
              maxHeight: 450,
            }}
          >
            {JSON.stringify(project, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}