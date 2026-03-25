import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  type ResumeResponse,
} from "../api/apiClient";

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString();
}

export default function ResumePage() {
  const { id } = useParams();
  const resumeId = id ?? "1";

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
        setError("No resume found yet. Create one from the resumes page first.");
      } finally {
        if (alive) setLoading(false);
      }
    }

    loadResume();

    return () => {
      alive = false;
    };
  }, [resumeId]);

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
      {loading && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
          }}
        >
          Loading resume...
        </div>
      )}

      {!loading && !resume && (
  <div
    style={{
      border: "1px solid #2a2a2a",
      borderRadius: 16,
      padding: 20,
      background: "#161616",
    }}
  >
    <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
      No resume found
    </div>
    <div style={{ color: "#999", marginBottom: 16 }}>
      Create a resume from the resumes page, then open it here to edit.
    </div>

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

    <Link
      to="/resumes"
      style={{
        display: "inline-block",
        padding: "10px 14px",
        borderRadius: 10,
        border: "1px solid #2a2a2a",
        background: "#1a1a1a",
        color: "#ddd",
        textDecoration: "none",
      }}
    >
      Go to Resumes
    </Link>
  </div>
)}

      {!loading && resume && (
        <>
          <div style={{ marginBottom: 20 }}>
  <Link
    to="/resumes"
    style={{
      color: "#6f7cff",
      textDecoration: "none",
      fontSize: 14,
    }}
  >
    ← Back to Resumes
  </Link>
</div>

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

          {success && (
            <div
              style={{
                border: "1px solid #22462b",
                borderRadius: 12,
                padding: 14,
                background: "#102015",
                color: "#8ad6a2",
                marginBottom: 16,
              }}
            >
              {success}
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
                    <div
                      style={{
                        marginBottom: 10,
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: 18 }}>
                        {item.title}
                      </div>

                      <div
                        style={{
                          fontSize: 13,
                          color: "#999",
                          marginTop: 4,
                        }}
                      >
                        {formatDate(item.start_date)} – {formatDate(item.end_date)}
                      </div>

                      {item.project_name && (
                        <div
                          style={{
                            fontSize: 13,
                            color: "#999",
                            marginTop: 4,
                          }}
                        >
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
                                  disabled={saving}
                                  style={{
                                    padding: "6px 10px",
                                    borderRadius: 10,
                                    border: "1px solid #2a2a2a",
                                    background: "transparent",
                                    color: "#ddd",
                                    cursor:
                                      saving
                                        ? "not-allowed"
                                        : "pointer",
                                    opacity: saving ? 0.7 : 1,
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
                                  style={{width: "100%",
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
                                    disabled={saving || !hasEditedBulletChanges}
                                    style={{
                                      padding: "8px 12px",
                                      borderRadius: 10,
                                      border: "1px solid #2a2a2a",
                                      background: "#1a1a1a",
                                      color: "#ddd",
                                      cursor:
                                      saving || !hasEditedBulletChanges
                                      ? "not-allowed"
                                      : "pointer",
                                      opacity: saving || !hasEditedBulletChanges ? 0.7 : 1,
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