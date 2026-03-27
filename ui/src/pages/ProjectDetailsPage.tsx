import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type ProjectInsightsResponse } from "../api/apiClient";

type ProjectReport = {
  project_name: string;
  user_config_used?: number | null;
  image_data?: string | null;
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

function getInsightId(projectName: string, insight: ProjectInsight, index: number) {
  return `${projectName}-${index}-${insight.message}`;
}

function isNotFoundError(msg: string) {
  return msg.includes("API request failed (404)");
}

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function getImageSrc(base64: string): string {
  if (base64.startsWith("/9j/")) return `data:image/jpeg;base64,${base64}`;
  if (base64.startsWith("iVBOR")) return `data:image/png;base64,${base64}`;
  if (base64.startsWith("R0lG")) return `data:image/gif;base64,${base64}`;
  if (base64.startsWith("UklG")) return `data:image/webp;base64,${base64}`;
  return `data:image/jpeg;base64,${base64}`;
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
  const [insightFeedbackError, setInsightFeedbackError] = useState<string | null>(null);
  const [updatingInsightIds, setUpdatingInsightIds] = useState<Record<string, boolean>>({});
  const [imageUploading, setImageUploading] = useState(false);
  const [imageRemoving, setImageRemoving] = useState(false);
  const [imageUploadError, setImageUploadError] = useState<string | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  async function handleImageUpload(file: File) {
    setImageUploading(true);
    setImageUploadError(null);
    try {
      await api.uploadProjectImage(projectName, file);
      const refreshed = (await api.getProject(projectName)) as ProjectReport;
      setProject(refreshed);
    } catch (e: any) {
      setImageUploadError(e?.message ?? "Failed to upload image");
    } finally {
      setImageUploading(false);
    }
  }

  async function handleImageRemove() {
    setImageRemoving(true);
    setImageUploadError(null);
    try {
      await api.deleteProjectImage(projectName);
      const refreshed = (await api.getProject(projectName)) as ProjectReport;
      setProject(refreshed);
    } catch (e: any) {
      setImageUploadError(e?.message ?? "Failed to remove image");
    } finally {
      setImageRemoving(false);
    }
  }

  async function handleInsightFeedback(
    insight: ProjectInsight,
    index: number,
    payload: { useful?: boolean; dismissed?: boolean }
  ) {
    if (!project) return;

    const insightId = getInsightId(project.project_name, insight, index);
    setInsightFeedbackError(null);
    setUpdatingInsightIds((current) => ({
      ...current,
      [insightId]: true,
    }));

    try {
      const response = await api.updateProjectInsightFeedback(project.project_name, {
        message: insight.message,
        ...payload,
      });
      setInsights(response.insights ?? []);
    } catch (e: any) {
      setInsightFeedbackError(e?.message ?? "Failed to update insight feedback");
    } finally {
      setUpdatingInsightIds((current) => {
        const next = { ...current };
        delete next[insightId];
        return next;
      });
    }
  }

  const visibleInsights = insights.filter((insight) => !insight.dismissed);

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
        setInsightFeedbackError(null);
        setUpdatingInsightIds({});

        const projectRes = (await api.getProject(projectName)) as ProjectReport;

        if (!alive) return;

        setProject(projectRes);
        setLoading(false);

        try {
          const insightsRes =
            (await api.getProjectInsights(projectName)) as ProjectInsightsResponse;

          if (!alive) return;
          setInsights(insightsRes.insights ?? []);
        } catch {
          if (!alive) return;
          setInsights([]);
        } finally {
          if (alive) {
            setInsightsLoading(false);
          }
        }
      } catch (e: any) {
        if (!alive) return;
        setError(e?.message ?? "Failed to load project");
        setLoading(false);
        setInsightsLoading(false);
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

          <div style={{ marginBottom: 24 }}>
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImageUpload(file);
                e.target.value = "";
              }}
            />

            {project.image_data ? (
              <div style={{ display: "inline-flex", flexDirection: "column", gap: 10 }}>
                <div
                  style={{
                    width: 240,
                    height: 240,
                    overflow: "hidden",
                    borderRadius: 12,
                    border: "1px solid #2a2a2a",
                    background: "#0d0d0d",
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <img
                    src={getImageSrc(project.image_data)}
                    alt="Project thumbnail"
                    style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
                  />
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    disabled={imageUploading || imageRemoving}
                    onClick={() => imageInputRef.current?.click()}
                    style={{
                      border: "1px solid #2a2a2a",
                      borderRadius: 8,
                      background: "transparent",
                      color: "#6f7cff",
                      padding: "6px 14px",
                      cursor: imageUploading || imageRemoving ? "not-allowed" : "pointer",
                      fontSize: 13,
                      opacity: imageUploading || imageRemoving ? 0.6 : 1,
                    }}
                  >
                    {imageUploading ? "Uploading…" : "Change Image"}
                  </button>
                  <button
                    type="button"
                    disabled={imageUploading || imageRemoving}
                    onClick={handleImageRemove}
                    style={{
                      border: "1px solid #4a2020",
                      borderRadius: 8,
                      background: "transparent",
                      color: "#ff8a8a",
                      padding: "6px 14px",
                      cursor: imageUploading || imageRemoving ? "not-allowed" : "pointer",
                      fontSize: 13,
                      opacity: imageUploading || imageRemoving ? 0.6 : 1,
                    }}
                  >
                    {imageRemoving ? "Removing…" : "Remove Thumbnail"}
                  </button>
                </div>
                {imageUploadError && (
                  <div style={{ color: "#ff8a8a", fontSize: 12 }}>
                    {imageUploadError}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <button
                  type="button"
                  disabled={imageUploading}
                  onClick={() => imageInputRef.current?.click()}
                  style={{
                    border: "1px dashed #3a3a3a",
                    borderRadius: 10,
                    background: "#161616",
                    color: "#6f7cff",
                    padding: "14px 24px",
                    cursor: imageUploading ? "not-allowed" : "pointer",
                    fontSize: 14,
                    opacity: imageUploading ? 0.6 : 1,
                  }}
                >
                  {imageUploading ? "Uploading…" : "+ Upload Project Thumbnail"}
                </button>
                <div style={{ marginTop: 8, color: "#666", fontSize: 12 }}>
                  Supported formats: PNG, JPEG, WebP, GIF · Recommended size: 512×512px or larger
                </div>
                {imageUploadError && (
                  <div style={{ marginTop: 6, color: "#ff8a8a", fontSize: 12 }}>
                    {imageUploadError}
                  </div>
                )}
              </div>
            )}
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

            {insightFeedbackError && (
              <div style={{ marginBottom: 12, color: "#ff8a8a", lineHeight: 1.6 }}>
                {insightFeedbackError}
              </div>
            )}

            {insightsLoading ? (
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                Loading resume insights...
              </div>
            ) : visibleInsights.length > 0 ? (
              <div style={{ display: "grid", gap: 12 }}>
                {insights.map((insight, index) => {
                  const insightId = getInsightId(project.project_name, insight, index);
                  const isDismissed = Boolean(insight.dismissed);
                  const isUseful = Boolean(insight.useful);
                  const isUpdating = Boolean(updatingInsightIds[insightId]);

                  if (isDismissed) {
                    return null;
                  }

                  return (
                    <div
                      key={insightId}
                      style={{
                        border: "1px solid #2a2a2a",
                        borderRadius: 14,
                        padding: 16,
                        background: isUseful ? "#1a2316" : "#111111",
                      }}
                    >
                      <div style={{ color: "#ddd", lineHeight: 1.7, marginBottom: 12 }}>
                        {insight.message}
                      </div>

                      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                        <button
                          type="button"
                          disabled={isUpdating}
                          onClick={() =>
                            handleInsightFeedback(insight, index, { useful: !isUseful })
                          }
                          style={{
                            border: "1px solid #355c2b",
                            borderRadius: 999,
                            background: isUseful ? "#355c2b" : "transparent",
                            color: isUseful ? "#f4ffe8" : "#9fce8a",
                            padding: "6px 12px",
                            cursor: isUpdating ? "not-allowed" : "pointer",
                            opacity: isUpdating ? 0.6 : 1,
                          }}
                        >
                          {isUseful ? "Marked useful" : "Mark useful"}
                        </button>
                        <button
                          type="button"
                          disabled={isUpdating}
                          onClick={() =>
                            handleInsightFeedback(insight, index, { dismissed: true })
                          }
                          style={{
                            border: "1px solid #4a2a2a",
                            borderRadius: 999,
                            background: "transparent",
                            color: "#ff9a9a",
                            padding: "6px 12px",
                            cursor: isUpdating ? "not-allowed" : "pointer",
                            opacity: isUpdating ? 0.6 : 1,
                          }}
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : insights.length > 0 ? (
              <div style={{ color: "#999", lineHeight: 1.6 }}>
                All current resume insights have been dismissed.
              </div>
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
              <div style={{ color: "#999" }}>No statistics available for this project.</div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
