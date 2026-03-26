import { useEffect, useMemo, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  api,
  type ListProjectsResponse,
  type ProjectListItem,
  type ResumeResponse,
  type UserConfigResponse,
} from "../api/apiClient";

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString();
}

export default function ResumePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const resumeId = id ?? "1";

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [successVisible, setSuccessVisible] = useState(false);
  const [resume, setResume] = useState<ResumeResponse | null>(null);

  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null);
  const [editingBulletIndex, setEditingBulletIndex] = useState<number | null>(null);
  const [editedBulletText, setEditedBulletText] = useState("");

  useEffect(() => {
    let alive = true;

    async function loadResume() {
      try {
        setLoading(true);
        setError(null);
        setSuccess(null);
        setEditingItemIndex(null);
        setEditingBulletIndex(null);
        setEditedBulletText("");

        const res = await api.getResume(resumeId);

        if (!alive) return;
        setResume(res);
      } catch (e: any) {
        if (!alive) return;
        setResume(null);
        // Treat 404 silently - show the "no resume" empty state
        const is404 =
          e?.status === 404 ||
          e?.message?.includes("404") ||
          e?.message?.toLowerCase().includes("not found");
        if (!is404) {
          setError(e?.message ?? "Failed to load resume.");
        }
      } finally {
        if (alive) setLoading(false);
      }
    }

    loadResume();

    return () => {
      alive = false;
    };
  }, [resumeId]);

  async function handleGenerateResume() {
    try {
      setGenerating(true);
      setError(null);
      setSuccess(null);

      const projectsResponse = (await api.getProjects()) as ListProjectsResponse;
      const projectNames = Array.isArray(projectsResponse?.projects)
        ? projectsResponse.projects
            .map((project: ProjectListItem) => project.project_name)
            .filter(Boolean)
        : [];

      if (projectNames.length === 0) {
        throw new Error("No uploaded projects found. Upload and mine a project first.");
      }

      let userConfigId: number | null = null;
      try {
        const userConfig = (await api.getUserConfig()) as UserConfigResponse;
        userConfigId = userConfig?.id ?? null;
      } catch {
        userConfigId = null;
      }

      const generatedResume = await api.generateResume({
        project_names: projectNames,
        user_config_id: userConfigId,
      });

      setResume(generatedResume);
      setSuccess("Resume generated successfully!");
      setSuccessVisible(true);

      window.setTimeout(() => {
        setSuccessVisible(false); // fade out
        window.setTimeout(() => {
          setSuccess(null);
          if (generatedResume?.id) {
            navigate(`/resume/${generatedResume.id}`);
          }
        }, 400); // wait for fade-out to finish before navigating
      }, 2000);

    } catch (e: any) {
      setError(e?.message ?? "Failed to generate resume.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSaveChanges() {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      if (!resume?.id) {
        throw new Error("Generate or load a real resume before saving changes.");
      }

      if (editingItemIndex === null || editingBulletIndex === null) {
        throw new Error("Select a bullet point to edit before saving.");
      }

      const trimmed = editedBulletText.trim();
      if (!trimmed) {
        throw new Error("Bullet point content cannot be empty.");
      }

      const updatedResume = await api.editResumeBulletPoint(resume.id, {
        resume_id: resume.id,
        item_index: editingItemIndex,
        bullet_point_index: editingBulletIndex,
        new_content: trimmed,
        append: false,
      });

      setResume(updatedResume);
      setEditingItemIndex(null);
      setEditingBulletIndex(null);
      setEditedBulletText("");
      setSuccess("Resume bullet point updated successfully.");

      window.setTimeout(() => {
        setSuccess(null);
      }, 2500);

    } catch (e: any) {
      setError(e?.message ?? "Failed to save resume.");
    } finally {
      setSaving(false);
    }
  }

  const isEditing = useMemo(
    () => editingItemIndex !== null && editingBulletIndex !== null,
    [editingItemIndex, editingBulletIndex]
  );

  const hasEditedBulletChanges = useMemo(() => {
    if (
      editingItemIndex === null ||
      editingBulletIndex === null ||
      !resume?.items?.[editingItemIndex]?.bullet_points?.[editingBulletIndex]
    ) {
      return false;
    }

    const originalBullet =
      resume.items[editingItemIndex].bullet_points[editingBulletIndex].trim();

    return editedBulletText.trim().length > 0 && editedBulletText.trim() !== originalBullet;
  }, [editedBulletText, editingItemIndex, editingBulletIndex, resume]);

  function handleStartEditing(itemIndex: number, bulletIndex: number, bullet: string) {
    setError(null);
    setSuccess(null);
    setEditingItemIndex(itemIndex);
    setEditingBulletIndex(bulletIndex);
    setEditedBulletText(bullet);
  }

  function handleCancelEditing() {
    setEditingItemIndex(null);
    setEditingBulletIndex(null);
    setEditedBulletText("");
  }

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>

      <style>{`
        @keyframes popIn {
          0%   { opacity: 0; transform: translate(-50%, -50%) scale(0.85); }
          100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        }
        @keyframes popOut {
          0%   { opacity: 1; transform: translate(-50%, -50%) scale(1); }
          100% { opacity: 0; transform: translate(-50%, -50%) scale(0.85); }
        }
      `}</style>

      {/* Success popup */}
      {success && (
        <div
          style={{
            position: "fixed",
            top: "50%",
            left: "50%",
            zIndex: 1000,
            background: "#102015",
            border: "1px solid #22462b",
            borderRadius: 16,
            padding: "28px 40px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
            boxShadow: "0 8px 40px rgba(0,0,0,0.7)",
            animation: `${successVisible ? "popIn" : "popOut"} 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) forwards`,
            pointerEvents: "none",
          }}
        >
          <div style={{ fontSize: 32 }}>✓</div>
          <div style={{ fontSize: 17, fontWeight: 700, color: "#8ad6a2" }}>
            {success}
          </div>
        </div>
      )}

      {/* Page header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <h1 style={{ margin: 0 }}>Resume</h1>

        <div style={{ display: "flex", gap: 12 }}>
          <button
            type="button"
            onClick={handleGenerateResume}
            disabled={generating || saving}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "1px solid #2a2a2a",
              background: "#1a1a1a",
              color: "#ddd",
              cursor: generating || saving ? "not-allowed" : "pointer",
              opacity: generating || saving ? 0.7 : 1,
            }}
          >
            {generating ? "Generating..." : "Generate Resume"}
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ color: "#999", padding: 20 }}>Loading resume...</div>
      )}

      {/* No-resume / empty state */}
      {!loading && !resume && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 32,
            background: "#161616",
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-start",
            gap: 12,
          }}
        >
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>No resume found</h2>
          <p style={{ margin: 0, color: "#999", lineHeight: 1.6 }}>
            Generate a resume from your uploaded projects to view and edit it here.
            <br />
            Upload and mine a project from the dashboard, then generate a resume.
          </p>

          {error && (
            <div
              style={{
                border: "1px solid #3a1f1f",
                borderRadius: 12,
                padding: 14,
                background: "#1a1111",
                color: "#ff8a8a",
                width: "100%",
                boxSizing: "border-box",
              }}
            >
              {error}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
            <button
              type="button"
              onClick={() => navigate("/")}
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                border: "1px solid #2a2a2a",
                background: "transparent",
                color: "#999",
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              ← Go to Dashboard
            </button>
          </div>
        </div>
      )}

      {/* Resume content when present */}
      {!loading && resume && (
        <>
          {error && (
            <div
              style={{
                border: "1px solid #3a1f1f",
                borderRadius: 12,
                padding: 14,
                background: "#1a1111",
                color: "#ff8a8a",
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          <section
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
            }}
          >
            <div style={{ marginBottom: 20 }}>
              <h2 style={{ marginTop: 0, marginBottom: 10 }}>Resume Items</h2>

              <div style={{ color: "#999", fontSize: 14, lineHeight: 1.6 }}>
                <div>Email: {resume.email || "—"}</div>
                <div>GitHub: {resume.github || "—"}</div>
                <div>
                  Skills: {resume.skills?.length ? resume.skills.join(", ") : "—"}
                </div>
              </div>
            </div>

            {!resume.items || resume.items.length === 0 ? (
              <div style={{ color: "#999" }}>No resume items found.</div>
            ) : (
              <div style={{ display: "grid", gap: 16 }}>
                {resume.items.map((item, index) => (
                  <div
                    key={`${item.title}-${index}`}
                    style={{
                      border: "1px solid #2a2a2a",
                      borderRadius: 14,
                      padding: 16,
                      background: "#101010",
                    }}
                  >
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ fontWeight: 700, fontSize: 18 }}>
                        {item.title}
                      </div>

                      <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                        {formatDate(item.start_date)} – {formatDate(item.end_date)}
                      </div>

                      {item.project_name && (
                        <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                          Source Project: {item.project_name}
                        </div>
                      )}
                    </div>

                    {item.bullet_points && item.bullet_points.length > 0 && (
                      <div style={{ display: "grid", gap: 10, marginBottom: 12 }}>
                        {item.bullet_points.map((bullet, bulletIndex) => {
                          const selected =
                            editingItemIndex === index &&
                            editingBulletIndex === bulletIndex;

                          return (
                            <div key={bulletIndex} style={{ display: "grid", gap: 10 }}>
                              <div
                                style={{
                                  display: "flex",
                                  gap: 12,
                                  alignItems: "flex-start",
                                  padding: 12,
                                  borderRadius: 12,
                                  border: selected
                                    ? "1px solid #4b5563"
                                    : "1px solid #2a2a2a",
                                  background: selected ? "#14181f" : "#111",
                                }}
                              >
                                <div style={{ color: "#999", lineHeight: 1.5 }}>•</div>

                                <div style={{ flex: 1, color: "#ddd", lineHeight: 1.6 }}>
                                  {bullet}
                                </div>

                                <button
                                  type="button"
                                  onClick={() =>
                                    handleStartEditing(index, bulletIndex, bullet)
                                  }
                                  disabled={saving || generating}
                                  style={{
                                    padding: "6px 10px",
                                    borderRadius: 10,
                                    border: "1px solid #2a2a2a",
                                    background: "transparent",
                                    color: "#ddd",
                                    cursor:
                                      saving || generating ? "not-allowed" : "pointer",
                                    opacity: saving || generating ? 0.7 : 1,
                                    whiteSpace: "nowrap",
                                  }}
                                >
                                  {selected ? "Editing" : "Edit"}
                                </button>
                              </div>

                              {selected && (
                                <div
                                  style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #2a2a2a",
                                    background: "#101010",
                                  }}
                                >
                                  <div
                                    style={{
                                      fontSize: 13,
                                      color: "#999",
                                      marginBottom: 8,
                                    }}
                                  >
                                    Editing selected bullet point
                                  </div>

                                  <textarea
                                    value={editedBulletText}
                                    onChange={(e) => setEditedBulletText(e.target.value)}
                                    rows={4}
                                    style={{
                                      width: "100%",
                                      boxSizing: "border-box",
                                      resize: "vertical",
                                      borderRadius: 10,
                                      border: "1px solid #2a2a2a",
                                      background: "#161616",
                                      color: "#fff",
                                      padding: 12,
                                      fontFamily: "inherit",
                                      fontSize: 14,
                                    }}
                                  />

                                  <div
                                    style={{
                                      display: "flex",
                                      justifyContent: "flex-end",
                                      marginTop: 10,
                                      gap: 10,
                                    }}
                                  >
                                    <button
                                      type="button"
                                      onClick={handleCancelEditing}
                                      disabled={saving}
                                      style={{
                                        padding: "8px 12px",
                                        borderRadius: 10,
                                        border: "1px solid #2a2a2a",
                                        background: "transparent",
                                        color: "#ddd",
                                        cursor: saving ? "not-allowed" : "pointer",
                                        opacity: saving ? 0.7 : 1,
                                      }}
                                    >
                                      Cancel Edit
                                    </button>

                                    <button
                                      type="button"
                                      onClick={handleSaveChanges}
                                      disabled={saving || generating || !hasEditedBulletChanges}
                                      style={{
                                        padding: "8px 12px",
                                        borderRadius: 10,
                                        border: "1px solid #2a2a2a",
                                        background: "#1a1a1a",
                                        color: "#ddd",
                                        cursor:
                                          saving || generating || !hasEditedBulletChanges
                                            ? "not-allowed"
                                            : "pointer",
                                        opacity:
                                          saving || generating || !hasEditedBulletChanges
                                            ? 0.7
                                            : 1,
                                      }}
                                    >
                                      {saving ? "Saving..." : "Save Changes"}
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {item.frameworks && item.frameworks.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {item.frameworks.map((framework, fwIndex) => (
                          <div
                            key={`${framework}-${fwIndex}`}
                            style={{
                              padding: "6px 10px",
                              borderRadius: 999,
                              border: "1px solid #2a2a2a",
                              background: "#161616",
                              fontSize: 12,
                              color: "#ddd",
                            }}
                          >
                            {framework}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}