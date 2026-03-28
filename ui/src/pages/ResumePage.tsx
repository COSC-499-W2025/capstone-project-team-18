import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  api,
  type ResumeResponse,
  type SkillsByExpertise,
} from "../api/apiClient";
import PillField from "../components/PillField";

// ─── Date helpers ─────────────────────────────────────────────────────────────

function toMonthInput(dateStr?: string | null): string {
  if (!dateStr) return "";
  return String(dateStr).slice(0, 7); // "YYYY-MM-DD" → "YYYY-MM"
}

function fromMonthInput(monthStr: string, fallback?: string | null): string {
  if (monthStr) return `${monthStr}-01`;
  if (fallback) return String(fallback).slice(0, 10);
  return "2000-01-01";
}

function formatMonthYear(value?: string | null): string {
  if (!value) return "—";
  const s = String(value);
  const normalized = s.length === 7 ? `${s}-02` : s; // avoid timezone shift on day 1
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

// ─── Shared ───────────────────────────────────────────────────────────────────

const SECTION_LABEL = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.07em",
  textTransform: "uppercase" as const,
  color: "#555",
  display: "block",
  marginBottom: 8,
};

function Toast({ message, type }: { message: string; type: "success" | "error" }) {
  const ok = type === "success";
  return (
    <div
      style={{
        border: `1px solid ${ok ? "#22462b" : "#3a1f1f"}`,
        borderRadius: 10,
        padding: "11px 16px",
        background: ok ? "#0e1f14" : "#1a1111",
        color: ok ? "#8ad6a2" : "#ff8a8a",
        fontSize: 13,
        marginBottom: 14,
      }}
    >
      {message}
    </div>
  );
}

// ─── Skills Section ───────────────────────────────────────────────────────────

type SkillsEditState = {
  expert: string[];
  intermediate: string[];
  exposure: string[];
  expertInput: string;
  intermediateInput: string;
  exposureInput: string;
};

const SKILL_CATS: {
  key: keyof SkillsByExpertise;
  inputKey: keyof SkillsEditState;
  label: string;
  color: string;
  border: string;
  bg: string;
}[] = [
  {
    key: "expert",
    inputKey: "expertInput",
    label: "Expert",
    color: "#6f7cff",
    border: "#6f7cff55",
    bg: "#6f7cff11",
  },
  {
    key: "intermediate",
    inputKey: "intermediateInput",
    label: "Intermediate",
    color: "#5ba89e",
    border: "#5ba89e55",
    bg: "#5ba89e11",
  },
  {
    key: "exposure",
    inputKey: "exposureInput",
    label: "Exposure",
    color: "#999",
    border: "#444",
    bg: "transparent",
  },
];

function initSkillsEdit(sbe?: SkillsByExpertise | null): SkillsEditState {
  return {
    expert: sbe?.expert ?? [],
    intermediate: sbe?.intermediate ?? [],
    exposure: sbe?.exposure ?? [],
    expertInput: "",
    intermediateInput: "",
    exposureInput: "",
  };
}

function SkillsSection({
  resumeId,
  skillsByExpertise,
  onUpdated,
  onError,
}: {
  resumeId: number;
  skillsByExpertise: SkillsByExpertise | null | undefined;
  onUpdated: (res: ResumeResponse) => void;
  onError: (msg: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<SkillsEditState>(() => initSkillsEdit(skillsByExpertise));

  useEffect(() => {
    setDraft(initSkillsEdit(skillsByExpertise));
  }, [skillsByExpertise]);

  function openEdit() {
    setDraft(initSkillsEdit(skillsByExpertise));
    setEditing(true);
  }

  async function handleSave() {
    try {
      setSaving(true);
      const res = await api.editResumeSkills(resumeId, {
        expert: draft.expert,
        intermediate: draft.intermediate,
        exposure: draft.exposure,
      });
      onUpdated(res);
      setEditing(false);
    } catch (e: any) {
      onError(e?.message ?? "Failed to save skills.");
    } finally {
      setSaving(false);
    }
  }

  const hasSkills =
    (skillsByExpertise?.expert?.length ?? 0) +
      (skillsByExpertise?.intermediate?.length ?? 0) +
      (skillsByExpertise?.exposure?.length ?? 0) >
    0;

  return (
    <div
      style={{
        border: "1px solid #2a2a2a",
        borderRadius: 14,
        padding: "16px 20px",
        background: "#161616",
        marginBottom: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <span style={SECTION_LABEL}>Skills</span>
        {!editing ? (
          <button
            onClick={openEdit}
            style={{
              padding: "4px 12px",
              borderRadius: 7,
              border: "1px solid #2a2a2a",
              background: "transparent",
              color: "#888",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Edit Skills
          </button>
        ) : (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setEditing(false)}
              disabled={saving}
              style={{
                padding: "4px 12px",
                borderRadius: 7,
                border: "1px solid #2a2a2a",
                background: "transparent",
                color: "#888",
                fontSize: 12,
                cursor: saving ? "not-allowed" : "pointer",
                opacity: saving ? 0.6 : 1,
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: "4px 14px",
                borderRadius: 7,
                border: "1px solid #3a3a3a",
                background: "#222",
                color: "#fff",
                fontSize: 12,
                cursor: saving ? "not-allowed" : "pointer",
                opacity: saving ? 0.6 : 1,
              }}
            >
              {saving ? "Saving..." : "Save Skills"}
            </button>
          </div>
        )}
      </div>

      {!editing ? (
        hasSkills ? (
          <div style={{ display: "grid", gap: 10 }}>
            {SKILL_CATS.map(({ key, label, color, border, bg }) => {
              const skills = skillsByExpertise?.[key] ?? [];
              if (!skills.length) return null;
              return (
                <div key={key} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color,
                      width: 90,
                      flexShrink: 0,
                      paddingTop: 4,
                    }}
                  >
                    {label}
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                    {skills.map((s) => (
                      <span
                        key={s}
                        style={{
                          padding: "3px 10px",
                          borderRadius: 999,
                          border: `1px solid ${border}`,
                          background: bg,
                          fontSize: 12,
                          color,
                        }}
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ fontSize: 13, color: "#555" }}>
            No skills yet. Click "Edit Skills" to add them.
          </div>
        )
      ) : (
        <div style={{ display: "grid", gap: 18 }}>
          {SKILL_CATS.map(({ key, inputKey, label, color, border, bg }) => (
            <PillField
              key={key}
              label={label}
              pills={draft[key] as string[]}
              inputValue={draft[inputKey] as string}
              pillColor={color}
              borderColor={border}
              bgColor={bg}
              placeholder={`Add ${label.toLowerCase()} skill…`}
              disabled={saving}
              onRemove={(v) =>
                setDraft((p) => ({ ...p, [key]: (p[key] as string[]).filter((x) => x !== v) }))
              }
              onInputChange={(v) => setDraft((p) => ({ ...p, [inputKey]: v }))}
              onAdd={(v) => {
                if (v && !(draft[key] as string[]).includes(v)) {
                  setDraft((p) => ({
                    ...p,
                    [key]: [...(p[key] as string[]), v],
                    [inputKey]: "",
                  }));
                } else {
                  setDraft((p) => ({ ...p, [inputKey]: "" }));
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── ItemCard ─────────────────────────────────────────────────────────────────

type ResumeItem = ResumeResponse["items"][number];

function ItemCard({
  resumeId,
  item,
  itemIndex,
  onUpdated,
  onError,
}: {
  resumeId: number;
  item: ResumeItem;
  itemIndex: number;
  onUpdated: (res: ResumeResponse) => void;
  onError: (msg: string) => void;
}) {
  // ── Meta (title + dates)
  const [editingMeta, setEditingMeta] = useState(false);
  const [titleDraft, setTitleDraft] = useState(item.title);
  const [startDraft, setStartDraft] = useState(toMonthInput(item.start_date));
  const [endDraft, setEndDraft] = useState(toMonthInput(item.end_date));
  const [savingMeta, setSavingMeta] = useState(false);
  const [metaError, setMetaError] = useState<string | null>(null);

  // ── Frameworks PillField
  const [frameworksDraft, setFrameworksDraft] = useState<string[]>(item.frameworks ?? []);
  const [newFwInput, setNewFwInput] = useState("");
  const [savingFw, setSavingFw] = useState(false);
  const [fwError, setFwError] = useState<string | null>(null);

  // ── Bullets
  const [editingBulletIdx, setEditingBulletIdx] = useState<number | null>(null);
  const [editedBulletText, setEditedBulletText] = useState("");
  const [addingBullet, setAddingBullet] = useState(false);
  const [newBulletText, setNewBulletText] = useState("");
  const [savingBullet, setSavingBullet] = useState(false);

  // Sync state when item prop updates from parent
  useEffect(() => {
    setTitleDraft(item.title);
    setStartDraft(toMonthInput(item.start_date));
    setEndDraft(toMonthInput(item.end_date));
    setFrameworksDraft(item.frameworks ?? []);
    setNewFwInput("");
  }, [item]);

  const fwDirty =
    JSON.stringify([...frameworksDraft].sort()) !==
    JSON.stringify([...(item.frameworks ?? [])].sort());

  const bulletHasChanges =
    editingBulletIdx !== null &&
    editedBulletText.trim().length > 0 &&
    editedBulletText.trim() !== (item.bullet_points?.[editingBulletIdx] ?? "").trim();

  // ── Handlers

  async function handleSaveMeta() {
    const title = titleDraft.trim();
    if (!title) {
      setMetaError("Title cannot be empty.");
      return;
    }
    try {
      setSavingMeta(true);
      setMetaError(null);
      const res = await api.editResumeItem(resumeId, {
        resume_id: resumeId,
        item_index: itemIndex,
        title,
        start_date: fromMonthInput(startDraft, item.start_date),
        end_date: fromMonthInput(endDraft, item.end_date),
      });
      onUpdated(res);
      setEditingMeta(false);
    } catch (e: any) {
      setMetaError(e?.message ?? "Failed to save.");
    } finally {
      setSavingMeta(false);
    }
  }

  async function handleSaveFrameworks() {
    try {
      setSavingFw(true);
      setFwError(null);
      const res = await api.editResumeFrameworks(resumeId, {
        item_index: itemIndex,
        frameworks: frameworksDraft,
      });
      onUpdated(res);
    } catch (e: any) {
      setFwError(e?.message ?? "Failed to save frameworks.");
    } finally {
      setSavingFw(false);
    }
  }

  async function handleSaveBullet() {
    if (editingBulletIdx === null) return;
    const trimmed = editedBulletText.trim();
    if (!trimmed) {
      onError("Bullet point cannot be empty.");
      return;
    }
    try {
      setSavingBullet(true);
      const res = await api.editResumeBulletPoint(resumeId, {
        resume_id: resumeId,
        item_index: itemIndex,
        bullet_point_index: editingBulletIdx,
        new_content: trimmed,
        append: false,
      });
      onUpdated(res);
      setEditingBulletIdx(null);
      setEditedBulletText("");
    } catch (e: any) {
      onError(e?.message ?? "Failed to save bullet.");
    } finally {
      setSavingBullet(false);
    }
  }

  async function handleDeleteBullet(bulletIndex: number) {
    try {
      setSavingBullet(true);
      const res = await api.deleteResumeBulletPoint(resumeId, {
        item_index: itemIndex,
        bullet_point_index: bulletIndex,
      });
      onUpdated(res);
      if (editingBulletIdx === bulletIndex) {
        setEditingBulletIdx(null);
        setEditedBulletText("");
      }
    } catch (e: any) {
      onError(e?.message ?? "Failed to delete bullet.");
    } finally {
      setSavingBullet(false);
    }
  }

  async function handleAddBullet() {
    const trimmed = newBulletText.trim();
    if (!trimmed) return;
    try {
      setSavingBullet(true);
      const res = await api.editResumeBulletPoint(resumeId, {
        resume_id: resumeId,
        item_index: itemIndex,
        new_content: trimmed,
        append: true,
      });
      onUpdated(res);
      setAddingBullet(false);
      setNewBulletText("");
    } catch (e: any) {
      onError(e?.message ?? "Failed to add bullet.");
    } finally {
      setSavingBullet(false);
    }
  }

  const btnBase = {
    borderRadius: 7,
    border: "1px solid #2a2a2a",
    background: "transparent",
    cursor: "pointer",
    fontFamily: "inherit",
  } as const;

  return (
    <div
      style={{
        border: "1px solid #222",
        borderRadius: 12,
        padding: "16px 18px",
        background: "#101010",
      }}
    >
      {/* ── TITLE ─────────────────────────────────────────────── */}
      {editingMeta ? (
        <div style={{ marginBottom: 10 }}>
          <div style={SECTION_LABEL}>Title</div>
          <input
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            disabled={savingMeta}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "8px 11px",
              borderRadius: 8,
              border: "1px solid #2a2a2a",
              background: "#111",
              color: "#fff",
              fontSize: 15,
              fontWeight: 600,
              fontFamily: "inherit",
              outline: "none",
            }}
          />
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 4,
          }}
        >
          <div style={{ fontWeight: 700, fontSize: 16 }}>{item.title}</div>
          <button
            onClick={() => {
              setEditingMeta(true);
              setMetaError(null);
            }}
            style={{ ...btnBase, padding: "3px 10px", color: "#666", fontSize: 12, marginLeft: 10, flexShrink: 0 }}
          >
            Edit
          </button>
        </div>
      )}

      {/* ── DATES ─────────────────────────────────────────────── */}
      {editingMeta ? (
        <div style={{ marginBottom: 12 }}>
          <div style={SECTION_LABEL}>Dates</div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input
              type="month"
              value={startDraft}
              onChange={(e) => setStartDraft(e.target.value)}
              disabled={savingMeta}
              style={{
                flex: 1,
                padding: "7px 10px",
                borderRadius: 8,
                border: "1px solid #2a2a2a",
                background: "#111",
                color: "#fff",
                fontSize: 13,
                outline: "none",
                colorScheme: "dark",
                fontFamily: "inherit",
              }}
            />
            <span style={{ color: "#555", fontSize: 13 }}>–</span>
            <input
              type="month"
              value={endDraft}
              onChange={(e) => setEndDraft(e.target.value)}
              disabled={savingMeta}
              style={{
                flex: 1,
                padding: "7px 10px",
                borderRadius: 8,
                border: "1px solid #2a2a2a",
                background: "#111",
                color: "#fff",
                fontSize: 13,
                outline: "none",
                colorScheme: "dark",
                fontFamily: "inherit",
              }}
            />
          </div>
        </div>
      ) : (
        <div style={{ fontSize: 12, color: "#555", marginBottom: 12 }}>
          {item.project_name && <span>{item.project_name} · </span>}
          {formatMonthYear(item.start_date)} – {formatMonthYear(item.end_date)}
        </div>
      )}

      {/* Meta save/cancel + error */}
      {editingMeta && (
        <>
          {metaError && <Toast message={metaError} type="error" />}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 14 }}>
            <button
              onClick={() => {
                setEditingMeta(false);
                setMetaError(null);
              }}
              disabled={savingMeta}
              style={{ ...btnBase, padding: "6px 12px", color: "#888", fontSize: 12, opacity: savingMeta ? 0.6 : 1 }}
            >
              Cancel
            </button>
            <button
              onClick={handleSaveMeta}
              disabled={savingMeta}
              style={{
                ...btnBase,
                padding: "6px 14px",
                border: "1px solid #3a3a3a",
                background: "#222",
                color: "#fff",
                fontSize: 12,
                opacity: savingMeta ? 0.6 : 1,
              }}
            >
              {savingMeta ? "Saving..." : "Save"}
            </button>
          </div>
        </>
      )}

      <div style={{ borderTop: "1px solid #1a1a1a", marginBottom: 14 }} />

      {/* ── FRAMEWORKS ────────────────────────────────────────── */}
      <div style={{ marginBottom: 14 }}>
        {fwError && <Toast message={fwError} type="error" />}
        <PillField
          label="Frameworks & Technologies"
          pills={frameworksDraft}
          inputValue={newFwInput}
          pillColor="#e08060"
          borderColor="#e0806044"
          bgColor="#e0806011"
          placeholder="Add a framework or technology…"
          disabled={savingFw}
          onRemove={(v) => setFrameworksDraft((p) => p.filter((x) => x !== v))}
          onInputChange={setNewFwInput}
          onAdd={(v) => {
            if (v && !frameworksDraft.includes(v)) setFrameworksDraft((p) => [...p, v]);
            setNewFwInput("");
          }}
        />
        {fwDirty && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
            <button
              onClick={handleSaveFrameworks}
              disabled={savingFw}
              style={{
                ...btnBase,
                padding: "5px 14px",
                border: "1px solid #3a3a3a",
                background: "#222",
                color: "#e08060",
                fontSize: 12,
                opacity: savingFw ? 0.6 : 1,
              }}
            >
              {savingFw ? "Saving..." : "Save Frameworks"}
            </button>
          </div>
        )}
      </div>

      <div style={{ borderTop: "1px solid #1a1a1a", marginBottom: 12 }} />

      {/* ── BULLET POINTS ─────────────────────────────────────── */}
      <div>
        <div style={SECTION_LABEL}>Bullet Points</div>
        <div style={{ display: "grid", gap: 6, marginBottom: 6 }}>
          {(item.bullet_points ?? []).map((bullet, bulletIndex) => {
            const isEditing = editingBulletIdx === bulletIndex;
            return (
              <div key={bulletIndex}>
                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "flex-start",
                    padding: "9px 12px",
                    borderRadius: 9,
                    border: isEditing ? "1px solid #3a3a5a" : "1px solid #1e1e1e",
                    background: isEditing ? "#0f1220" : "#111",
                  }}
                >
                  <div style={{ color: "#555", lineHeight: 1.6, flexShrink: 0 }}>•</div>
                  <div style={{ flex: 1, color: "#ccc", lineHeight: 1.6, fontSize: 13 }}>
                    {bullet}
                  </div>
                  <div style={{ display: "flex", gap: 5, flexShrink: 0 }}>
                    <button
                      onClick={() => {
                        if (isEditing) {
                          setEditingBulletIdx(null);
                          setEditedBulletText("");
                        } else {
                          setEditingBulletIdx(bulletIndex);
                          setEditedBulletText(bullet);
                        }
                      }}
                      disabled={savingBullet}
                      style={{
                        ...btnBase,
                        padding: "3px 9px",
                        background: isEditing ? "#1a1a2e" : "transparent",
                        color: isEditing ? "#8888ff" : "#777",
                        fontSize: 11,
                        opacity: savingBullet ? 0.6 : 1,
                      }}
                    >
                      {isEditing ? "Editing" : "Edit"}
                    </button>
                    <button
                      onClick={() => handleDeleteBullet(bulletIndex)}
                      disabled={savingBullet}
                      style={{
                        ...btnBase,
                        padding: "3px 7px",
                        color: "#663333",
                        fontSize: 12,
                        opacity: savingBullet ? 0.6 : 1,
                      }}
                    >
                      ×
                    </button>
                  </div>
                </div>

                {isEditing && (
                  <div
                    style={{
                      padding: "10px 12px",
                      borderRadius: 9,
                      border: "1px solid #2a2a2a",
                      background: "#0d0d0d",
                      marginTop: 4,
                    }}
                  >
                    <textarea
                      value={editedBulletText}
                      onChange={(e) => setEditedBulletText(e.target.value)}
                      rows={3}
                      disabled={savingBullet}
                      style={{
                        width: "100%",
                        boxSizing: "border-box",
                        resize: "vertical",
                        borderRadius: 7,
                        border: "1px solid #2a2a2a",
                        background: "#161616",
                        color: "#fff",
                        padding: "9px 11px",
                        fontFamily: "inherit",
                        fontSize: 13,
                        lineHeight: 1.6,
                        outline: "none",
                      }}
                    />
                    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 7, gap: 7 }}>
                      <button
                        onClick={() => {
                          setEditingBulletIdx(null);
                          setEditedBulletText("");
                        }}
                        disabled={savingBullet}
                        style={{ ...btnBase, padding: "5px 11px", color: "#888", fontSize: 12, opacity: savingBullet ? 0.6 : 1 }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveBullet}
                        disabled={savingBullet || !bulletHasChanges}
                        style={{
                          ...btnBase,
                          padding: "5px 13px",
                          border: "1px solid #3a3a3a",
                          background: "#222",
                          color: bulletHasChanges ? "#fff" : "#555",
                          fontSize: 12,
                          opacity: savingBullet || !bulletHasChanges ? 0.6 : 1,
                        }}
                      >
                        {savingBullet ? "Saving..." : "Save"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Add bullet */}
        {!addingBullet ? (
          <button
            onClick={() => setAddingBullet(true)}
            style={{
              ...btnBase,
              padding: "7px 14px",
              border: "1px dashed #2a2a2a",
              color: "#555",
              fontSize: 12,
              width: "100%",
              textAlign: "left",
            }}
          >
            + Add bullet point
          </button>
        ) : (
          <div
            style={{
              padding: "10px 12px",
              borderRadius: 9,
              border: "1px solid #2a2a2a",
              background: "#0d0d0d",
            }}
          >
            <textarea
              value={newBulletText}
              onChange={(e) => setNewBulletText(e.target.value)}
              rows={3}
              placeholder="Describe what you did or achieved…"
              disabled={savingBullet}
              autoFocus
              style={{
                width: "100%",
                boxSizing: "border-box",
                resize: "vertical",
                borderRadius: 7,
                border: "1px solid #2a2a2a",
                background: "#161616",
                color: "#fff",
                padding: "9px 11px",
                fontFamily: "inherit",
                fontSize: 13,
                lineHeight: 1.6,
                outline: "none",
              }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 7, gap: 7 }}>
              <button
                onClick={() => {
                  setAddingBullet(false);
                  setNewBulletText("");
                }}
                disabled={savingBullet}
                style={{ ...btnBase, padding: "5px 11px", color: "#888", fontSize: 12, opacity: savingBullet ? 0.6 : 1 }}
              >
                Cancel
              </button>
              <button
                onClick={handleAddBullet}
                disabled={savingBullet || !newBulletText.trim()}
                style={{
                  ...btnBase,
                  padding: "5px 13px",
                  border: "1px solid #3a3a3a",
                  background: "#222",
                  color: newBulletText.trim() ? "#fff" : "#555",
                  fontSize: 12,
                  opacity: savingBullet || !newBulletText.trim() ? 0.6 : 1,
                }}
              >
                {savingBullet ? "Adding..." : "Add Bullet"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ResumePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const backTo: string = (location.state as any)?.from ?? "/resumes";
  const backLabel = backTo === "/" ? "← Back to Dashboard" : "← Back to Resumes";
  const resumeId = id ?? "1";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [resume, setResume] = useState<ResumeResponse | null>(null);

  // Title editing
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [savingTitle, setSavingTitle] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Delete
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        setSuccess(null);
        const res = await api.getResume(resumeId);
        if (!alive) return;
        setResume(res);
        setTitleDraft(res.title ?? "");
      } catch {
        if (!alive) return;
        setResume(null);
        setError("No resume found. Create one from the resumes page first.");
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [resumeId]);

  function showSuccess(msg: string) {
    setSuccess(msg);
    window.setTimeout(() => setSuccess(null), 2500);
  }

  function handleUpdated(res: ResumeResponse) {
    setResume(res);
    showSuccess("Saved.");
  }

  async function handleSaveTitle() {
    setSavingTitle(true);
    setSaveError(null);
    try {
      const res = await api.editResumeTitle(Number(resumeId), {
        title: titleDraft.trim() || null,
      });
      setResume(res);
      setEditingTitle(false);
    } catch (e: any) {
      setSaveError(e?.message ?? "Failed to save.");
    } finally {
      setSavingTitle(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteResume(Number(resumeId));
      navigate("/resumes");
    } catch (e: any) {
      setDeleteError(e?.message ?? "Failed to delete.");
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 24, paddingTop: 40, maxWidth: 800, margin: "0 auto" }}>
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 14,
            padding: 20,
            background: "#161616",
            color: "#555",
            fontSize: 14,
          }}
        >
          Loading resume...
        </div>
      </div>
    );
  }

  if (!resume) {
    return (
      <div style={{ padding: 24, paddingTop: 40, maxWidth: 800, margin: "0 auto" }}>
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 14,
            padding: 28,
            background: "#161616",
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No resume found</div>
          <div style={{ color: "#666", marginBottom: 20, fontSize: 14 }}>
            {error ?? "Create a resume from the resumes page."}
          </div>
          <Link
            to={backTo}
            style={{
              display: "inline-block",
              padding: "9px 16px",
              borderRadius: 9,
              border: "1px solid #2a2a2a",
              background: "#1a1a1a",
              color: "#ddd",
              textDecoration: "none",
              fontSize: 14,
            }}
          >
            {backTo === "/" ? "← Go to Dashboard" : "← Go to Resumes"}
          </Link>
        </div>
      </div>
    );
  }

  const displayTitle = resume.title || `Resume #${resume.id}`;

  return (
    <div style={{ padding: 24, paddingTop: 40, maxWidth: 800, margin: "0 auto" }}>
      {/* Back */}
      <Link to={backTo} style={{ color: "#6f7cff", textDecoration: "none", fontSize: 14 }}>
        {backLabel}
      </Link>

      {/* Header */}
      <div
        style={{
          marginTop: 20,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
          marginBottom: 24,
        }}
      >
        {/* Title */}
        <div>
          {editingTitle ? (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveTitle();
                  if (e.key === "Escape") setEditingTitle(false);
                }}
                placeholder="Resume title…"
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  padding: "6px 10px",
                  borderRadius: 10,
                  border: "1px solid #2a2a2a",
                  background: "#111",
                  color: "#fff",
                  minWidth: 280,
                  fontFamily: "inherit",
                  outline: "none",
                }}
                autoFocus
              />
              <button
                onClick={() => setEditingTitle(false)}
                style={{
                  padding: "6px 12px",
                  borderRadius: 10,
                  border: "1px solid #2a2a2a",
                  background: "transparent",
                  color: "#ddd",
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTitle}
                disabled={savingTitle}
                style={{
                  padding: "6px 12px",
                  borderRadius: 10,
                  border: "1px solid #2a2a2a",
                  background: "transparent",
                  color: savingTitle ? "#666" : "#ddd",
                  cursor: savingTitle ? "not-allowed" : "pointer",
                  fontSize: 14,
                  opacity: savingTitle ? 0.6 : 1,
                }}
              >
                Apply
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ margin: 0, fontSize: 28 }}>{displayTitle}</h1>
              <button
                onClick={() => setEditingTitle(true)}
                style={{
                  padding: "4px 8px",
                  borderRadius: 8,
                  border: "1px solid #2a2a2a",
                  background: "transparent",
                  color: "#999",
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                Edit
              </button>
            </div>
          )}
        </div>

        {/* Action bar */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={handleSaveTitle}
            disabled={savingTitle}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "1px solid #3a3a3a",
              background: "#1f1f1f",
              color: "#fff",
              cursor: savingTitle ? "not-allowed" : "pointer",
              fontSize: 14,
              opacity: savingTitle ? 0.6 : 1,
            }}
          >
            {savingTitle ? "Saving..." : "Save"}
          </button>

          <button
            disabled
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid #2a2a2a",
              borderRadius: 10,
              color: "#555",
              cursor: "not-allowed",
              fontSize: 14,
              opacity: 0.5,
            }}
          >
            Export
          </button>

          <button
            onClick={() => setShowDeleteConfirm(true)}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid #3a1111",
              borderRadius: 10,
              color: "#ff8a8a",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Delete
          </button>
        </div>
      </div>

      {saveError && (
        <div style={{ color: "#ff8a8a", fontSize: 14, marginBottom: 14 }}>{saveError}</div>
      )}

      {error && <Toast message={error} type="error" />}
      {success && <Toast message={success} type="success" />}

      {/* Skills */}
      <SkillsSection
        resumeId={resume.id!}
        skillsByExpertise={resume.skills_by_expertise}
        onUpdated={(res) => {
          setResume(res);
          showSuccess("Skills saved.");
        }}
        onError={(msg) => setError(msg)}
      />

      {/* Projects */}
      <div
        style={{
          border: "1px solid #2a2a2a",
          borderRadius: 14,
          padding: "16px 20px",
          background: "#161616",
        }}
      >
        <span style={SECTION_LABEL}>Projects</span>

        {!resume.items || resume.items.length === 0 ? (
          <div style={{ fontSize: 13, color: "#555" }}>No projects in this resume.</div>
        ) : (
          <div style={{ display: "grid", gap: 14 }}>
            {resume.items.map((item, itemIndex) => (
              <ItemCard
                key={`${item.title}-${itemIndex}`}
                resumeId={resume.id!}
                item={item}
                itemIndex={itemIndex}
                onUpdated={handleUpdated}
                onError={(msg) => setError(msg)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div
          onClick={() => { if (!deleting) setShowDeleteConfirm(false); }}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.68)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 24,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "100%",
              maxWidth: 400,
              background: "#1b1b1b",
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 24,
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Delete Resume</h2>
            <p style={{ color: "#ccc", lineHeight: 1.6 }}>
              Are you sure you want to delete{" "}
              <strong>"{displayTitle}"</strong>? This will permanently remove
              the resume and all its content. This cannot be undone.
            </p>

            {deleteError && (
              <div
                style={{
                  color: "#ff8a8a",
                  fontSize: 14,
                  marginBottom: 16,
                  padding: "8px 12px",
                  background: "#3a1111",
                  borderRadius: 8,
                }}
              >
                {deleteError}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid #2a2a2a",
                  background: "transparent",
                  color: deleting ? "#666" : "#ddd",
                  cursor: deleting ? "not-allowed" : "pointer",
                }}
              >
                Cancel
              </button>

              <button
                onClick={handleDelete}
                disabled={deleting}
                style={{
                  padding: "10px 16px",
                  borderRadius: 10,
                  border: "1px solid #3a1111",
                  background: deleting ? "#202020" : "#3a1111",
                  color: "#ff8a8a",
                  cursor: deleting ? "not-allowed" : "pointer",
                  opacity: deleting ? 0.7 : 1,
                }}
              >
                {deleting ? "Deleting..." : "Delete Resume"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
