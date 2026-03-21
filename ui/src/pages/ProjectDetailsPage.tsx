import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type ProjectInsightsResponse } from "../api/apiClient";

type ProjectReport = {
  project_name: string;
  user_config_used?: number | null;
  image_data?: unknown | null;
  created_at?: string;
  last_updated?: string;
  description?: string;
  summary?: string;
  overview?: string;
  skills?: string[];
  frameworks?: string[];
  bullet_points?: string[];
  highlights?: string[];
  statistic?: Record<string, unknown>;
  [key: string]: unknown;
};

type ProjectInsight = ProjectInsightsResponse["insights"][number];

function isNotFoundError(msg: string) {
  return msg.includes("API request failed (404)");
}

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function formatStatisticValue(value: unknown): string {
  if (value === null || value === undefined) return "—";

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    return JSON.stringify(value, null, 2);
  }

  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;

    if ("value" in obj && obj.value !== undefined) {
      if (
        typeof obj.value === "string" ||
        typeof obj.value === "number" ||
        typeof obj.value === "boolean"
      ) {
        return String(obj.value);
      }
      return JSON.stringify(obj.value, null, 2);
    }

    return JSON.stringify(obj, null, 2);
  }

  return String(value);
}

export default function ProjectDetailsPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const projectName = id ?? "";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectReport | null>(null);
  const [insights, setInsights] = useState<ProjectInsight[]>([]);
  const [insightsLoading, setInsightsLoading] = useState(false);

  const projectStatistics =
    project?.statistic && typeof project.statistic === "object"
      ? Object.entries(project.statistic).sort(([a], [b]) => {
          if (a === "PROJECT_START_DATE" && b === "PROJECT_END_DATE") return -1;
          if (a === "PROJECT_END_DATE" && b === "PROJECT_START_DATE") return 1;
          return 0;
        })
      : [];

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
        setInsights([]);
        setInsightsLoading(true);

        const [projectRes, insightsRes] = await Promise.all([
          api.getProject(projectName) as Promise<ProjectReport>,
          api.getProjectInsights(projectName) as Promise<ProjectInsightsResponse>,
        ]);

        if (!alive) return;

        setProject(projectRes);
        setInsights(insightsRes.insights ?? []);
      } catch (e: any) {
        if (!alive) return;
        setError(e?.message ?? "Failed to load project");
      } finally {
        if (alive) {
          setLoading(false);
          setInsightsLoading(false);
        }
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
              <strong>Not found:</strong> No project named <code>{projectName}</code>
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
              marginBottom: 24,
            }}
          >
            <h1 style={{ margin: 0 }}>{project.project_name}</h1>
            <p style={{ marginTop: 8, color: "#666" }}>
              Review uploaded project metadata and mined output.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
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

            {project.user_config_used !== null &&
              project.user_config_used !== undefined && (
                <section
                  style={{
                    border: "1px solid #2a2a2a",
                    borderRadius: 16,
                    padding: 18,
                    background: "#161616",
                  }}
                >
                  <div style={{ fontSize: 13, color: "#999", marginBottom: 8 }}>
                    User Config Used
                  </div>
                  <div style={{ fontWeight: 600 }}>
                    {project.user_config_used}
                  </div>
                </section>
              )}
          </div>

          <section
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
              marginBottom: 24,
            }}
          >
            <h2 style={{ marginTop: 0 }}>Resume Insights</h2>
            <p style={{ marginTop: 0, color: "#999", lineHeight: 1.6 }}>
              Project-specific prompts to help turn this work into stronger resume bullets.
            </p>

            {insightsLoading ? (
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                Loading resume insights...
              </div>
            ) : insights.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 12 }}>
                {insights.map((insight, index) => (
                  <li key={`${project.project_name}-insight-${index}`} style={{ color: "#ddd", lineHeight: 1.7 }}>
                    {insight.message}
                  </li>
                ))}
              </ul>
            ) : (
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                No resume insights are currently available for this project.
              </div>
            )}
          </section>

          <section
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
              marginBottom: 24,
            }}
          >
            <h2 style={{ marginTop: 0 }}>Statistics</h2>

            {projectStatistics.length > 0 ? (
              <div style={{ display: "grid", gap: 10 }}>
                {projectStatistics.map(([key, value]) => (
                  <div
                    key={key}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "280px 1fr",
                      gap: 16,
                      paddingBottom: 10,
                      borderBottom: "1px solid #222",
                      alignItems: "start",
                    }}
                  >
                    <span style={{ color: "#999", textTransform: "capitalize" }}>
                      {key.replace(/_/g, " ")}
                    </span>

                    <pre
                      style={{
                        margin: 0,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        color: "#ddd",
                        fontSize: 13,
                        fontFamily: "inherit",
                        lineHeight: 1.6,
                        background: "transparent",
                      }}
                    >
                      {formatStatisticValue(value)}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                No statistics are currently available for this project.
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}