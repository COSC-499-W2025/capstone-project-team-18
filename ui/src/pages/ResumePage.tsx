import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  api,
  type ResumeResponse,
  type SkillsByExpertise,
} from "../api/apiClient";
import PillField from "../components/PillField";
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

// ─── Date helpers ─────────────────────────────────────────────────────────────

function toMonthInput(dateStr?: string | null): string {
  if (!dateStr) return "";
  return String(dateStr).slice(0, 7); // "YYYY-MM-DD" becomes "YYYY-MM"
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
  fontSize: 13,
  fontWeight: 700,
  letterSpacing: "0.07em",
  textTransform: "uppercase" as const,
  color: "var(--text-secondary)",
  display: "block",
  marginBottom: 8,
};

// ─── Page overflow estimator ──────────────────────────────────────────────────
// Approximates line usage based on the Jake Gutierrez LaTeX template at 11pt.
// A single page holds roughly 55 content lines with 0.7in margins.
const LINES_PER_PAGE = 55;

function estimateResumeLines(resume: ResumeResponse): number {
  let lines = 0;

  // Header: name + contact row
  lines += 2;

  // Each section heading costs ~1.5 lines (title + rule + spacing)
  const sectionHeading = 1.5;

  if (resume.education && resume.education.length > 0) {
    lines += sectionHeading + resume.education.length;
  }
  if (resume.awards && resume.awards.length > 0) {
    lines += sectionHeading + resume.awards.length;
  }
  if (resume.items && resume.items.length > 0) {
    lines += sectionHeading;
    for (const item of resume.items) {
      // Project heading row
      lines += 1;
      // Each bullet wraps at ~90 chars; average bullet is ~120 chars → ~1.5 lines
      for (const b of item.bullet_points ?? []) {
        lines += Math.max(1, Math.ceil(b.length / 90));
      }
    }
  }
  if (resume.skills && resume.skills.length > 0) {
    lines += sectionHeading + 1;
  }

  return lines;
}

function Toast({ message, type }: { message: string; type: "success" | "error" }) {
  const ok = type === "success";
  return (
    <div
      style={{
        border: `1px solid ${ok ? "#b2dfb2" : "var(--danger-bg-strong)"}`,
        borderRadius: 10,
        padding: "11px 16px",
        background: ok ? "#f0faf0" : "var(--danger-bg)",
        color: ok ? "#155724" : "var(--danger-text)",
        fontSize: 15,
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
    color: "#0055B7",
    border: "#93c5fd",
    bg: "#dbeafe",
  },
  {
    key: "intermediate",
    inputKey: "intermediateInput",
    label: "Intermediate",
    color: "#0f766e",
    border: "#5eead4",
    bg: "#ccfbf1",
  },
  {
    key: "exposure",
    inputKey: "exposureInput",
    label: "Exposure",
    color: "#6b7280",
    border: "#d1d5db",
    bg: "#f3f4f6",
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
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "16px 20px",
        background: "var(--bg-surface)",
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
              border: "none",
              background: "var(--btn-primary)",
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
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
                border: "1px solid var(--border)",
                background: "transparent",
                color: "var(--text-secondary)",
                fontSize: 14,
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
                border: "none",
                background: saving ? "var(--bg-surface-deep)" : "var(--btn-primary)",
                color: saving ? "var(--text-muted)" : "#fff",
                fontSize: 14,
                fontWeight: 600,
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
                      fontSize: 13,
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
                          fontSize: 14,
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
          <div style={{ fontSize: 15, color: "var(--text-secondary)" }}>
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

  // ── Insights
  const [showInsights, setShowInsights] = useState(false);
  const [insightsLoaded, setInsightsLoaded] = useState(false);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState<string | null>(null);
  const [visibleInsights, setVisibleInsights] = useState<string[]>([]);
  const [insightsCache, setInsightsCache] = useState<string[]>([]);

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

  async function handleToggleInsights() {
    if (showInsights) {
      setShowInsights(false);
      return;
    }
    setShowInsights(true);
    if (insightsLoaded) return;

    if (!item.project_name) {
      setInsightsError("No project associated with this resume item.");
      return;
    }

    try {
      setInsightsLoading(true);
      setInsightsError(null);
      const res = await api.getProjectInsights(item.project_name);
      const all = res.insights.map((i) => i.message);
      setVisibleInsights(all.slice(0, 3));
      setInsightsCache(all.slice(3));
      setInsightsLoaded(true);
    } catch (e: any) {
      setInsightsError(e?.message ?? "Failed to load writing prompts.");
    } finally {
      setInsightsLoading(false);
    }
  }

  async function handleDismissInsight(message: string, idx: number) {
    setVisibleInsights((prev) => {
      const updated = [...prev];
      if (insightsCache.length > 0) {
        updated[idx] = insightsCache[0];
      } else {
        updated.splice(idx, 1);
      }
      return updated;
    });
    setInsightsCache((prev) => prev.slice(1));
    if (!item.project_name) return;
    try {
      await api.dismissInsight(item.project_name, message);
    } catch {
      // dismissed locally even if the network call fails
    }
  }

  const btnBase = {
    borderRadius: 7,
    border: "1px solid var(--border)",
    background: "transparent",
    cursor: "pointer",
    fontFamily: "inherit",
  } as const;

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "16px 18px",
        background: "var(--bg-surface-deep)",
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
              border: "1px solid var(--border)",
              background: "var(--bg-input)",
              color: "var(--text-primary)",
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
            style={{ ...btnBase, padding: "3px 10px", border: "1px solid var(--btn-primary)", color: "var(--btn-primary)", fontSize: 14, marginLeft: 10, flexShrink: 0, fontWeight: 500 }}
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
                border: "1px solid var(--border)",
                background: "var(--bg-input)",
                color: "var(--text-primary)",
                fontSize: 14,
                outline: "none",
                colorScheme: "light",
                fontFamily: "inherit",
              }}
            />
            <span style={{ color: "var(--text-secondary)", fontSize: 14 }}>–</span>
            <input
              type="month"
              value={endDraft}
              onChange={(e) => setEndDraft(e.target.value)}
              disabled={savingMeta}
              style={{
                flex: 1,
                padding: "7px 10px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--bg-input)",
                color: "var(--text-primary)",
                fontSize: 14,
                outline: "none",
                colorScheme: "light",
                fontFamily: "inherit",
              }}
            />
          </div>
        </div>
      ) : (
        <div style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 12 }}>
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
              style={{ ...btnBase, padding: "6px 12px", color: "var(--text-muted)", fontSize: 14, opacity: savingMeta ? 0.6 : 1 }}
            >
              Cancel
            </button>
            <button
              onClick={handleSaveMeta}
              disabled={savingMeta}
              style={{
                ...btnBase,
                padding: "6px 14px",
                border: "none",
                background: savingMeta ? "var(--bg-surface-deep)" : "var(--btn-primary)",
                color: savingMeta ? "var(--text-muted)" : "#fff",
                fontSize: 14,
                fontWeight: 600,
                opacity: savingMeta ? 0.6 : 1,
              }}
            >
              {savingMeta ? "Saving..." : "Save"}
            </button>
          </div>
        </>
      )}

      <div style={{ borderTop: "1px solid var(--border)", marginBottom: 14 }} />

      {/* ── FRAMEWORKS ────────────────────────────────────────── */}
      <div style={{ marginBottom: 14 }}>
        {fwError && <Toast message={fwError} type="error" />}
        <PillField
          label="Frameworks & Technologies"
          pills={frameworksDraft}
          inputValue={newFwInput}
          pillColor="#6d28d9"
          borderColor="#c4b5fd"
          bgColor="#ede9fe"
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
                border: "none",
                background: savingFw ? "var(--bg-surface-deep)" : "var(--btn-primary)",
                color: savingFw ? "var(--text-muted)" : "#fff",
                fontSize: 14,
                fontWeight: 600,
                opacity: savingFw ? 0.6 : 1,
              }}
            >
              {savingFw ? "Saving..." : "Save Frameworks"}
            </button>
          </div>
        )}
      </div>

      <div style={{ borderTop: "1px solid var(--border)", marginBottom: 12 }} />

      {/* ── BULLET POINTS ─────────────────────────────────────── */}
      <div>
        {/* Header row: label + sparkles button */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={SECTION_LABEL}>Bullet Points</span>
          {item.project_name && (
            <button
              onClick={handleToggleInsights}
              disabled={insightsLoading}
              style={{
                padding: "3px 10px",
                borderRadius: 7,
                border: `1px solid ${showInsights ? "#8b5cf6" : "var(--border)"}`,
                background: showInsights ? "#faf5ff" : "transparent",
                color: insightsLoading ? "var(--text-muted)" : "#7c3aed",
                fontSize: 13,
                cursor: insightsLoading ? "wait" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4,
                fontFamily: "inherit",
              }}
            >
              ✦ {insightsLoading ? "Loading…" : "Writing prompts"}
            </button>
          )}
        </div>

        {/* Content row: bullets left, insights right */}
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

          {/* Left: bullet list + add button */}
          <div style={{ flex: 1, minWidth: 0 }}>
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
                        border: isEditing ? "1px solid var(--hover-border)" : "1px solid var(--border)",
                        background: isEditing ? "var(--hover-bg)" : "var(--bg-input)",
                      }}
                    >
                      <div style={{ color: "var(--text-secondary)", lineHeight: 1.6, flexShrink: 0 }}>•</div>
                      <div style={{ flex: 1, color: "var(--text-secondary)", lineHeight: 1.6, fontSize: 15 }}>
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
                            background: isEditing ? "var(--hover-bg)" : "transparent",
                            color: isEditing ? "var(--accent)" : "var(--text-muted)",
                            fontSize: 13,
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
                            color: "var(--danger-text)",
                            fontSize: 14,
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
                          border: "1px solid var(--border)",
                          background: "var(--bg-surface-deep)",
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
                            border: "1px solid var(--border)",
                            background: "var(--bg-surface)",
                            color: "var(--text-primary)",
                            padding: "9px 11px",
                            fontFamily: "inherit",
                            fontSize: 15,
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
                            style={{ ...btnBase, padding: "5px 11px", color: "var(--text-muted)", fontSize: 13, opacity: savingBullet ? 0.6 : 1 }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSaveBullet}
                            disabled={savingBullet || !bulletHasChanges}
                            style={{
                              ...btnBase,
                              padding: "5px 13px",
                              border: "none",
                              background: bulletHasChanges && !savingBullet ? "var(--btn-primary)" : "var(--bg-surface-deep)",
                              color: bulletHasChanges && !savingBullet ? "#fff" : "var(--text-muted)",
                              fontWeight: 600,
                              fontSize: 13,
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
                  border: "1px dashed var(--btn-primary)",
                  color: "var(--btn-primary)",
                  fontSize: 14,
                  fontWeight: 500,
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
                  border: "1px solid var(--border)",
                  background: "var(--bg-surface-deep)",
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
                    border: "1px solid var(--border)",
                    background: "var(--bg-surface)",
                    color: "var(--text-primary)",
                    padding: "9px 11px",
                    fontFamily: "inherit",
                    fontSize: 15,
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
                    style={{ ...btnBase, padding: "5px 11px", color: "var(--text-muted)", fontSize: 13, opacity: savingBullet ? 0.6 : 1 }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddBullet}
                    disabled={savingBullet || !newBulletText.trim()}
                    style={{
                      ...btnBase,
                      padding: "5px 13px",
                      border: "none",
                      background: newBulletText.trim() && !savingBullet ? "var(--btn-primary)" : "var(--bg-surface-deep)",
                      color: newBulletText.trim() && !savingBullet ? "#fff" : "var(--text-muted)",
                      fontWeight: 600,
                      fontSize: 13,
                      opacity: savingBullet || !newBulletText.trim() ? 0.6 : 1,
                    }}
                  >
                    {savingBullet ? "Adding..." : "Add Bullet"}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Right: insights panel */}
          {showInsights && !insightsLoading && (
            <div
              style={{
                width: 320,
                flexShrink: 0,
                borderRadius: 10,
                border: "1px solid #c4b5fd",
                background: "#faf5ff",
                padding: "12px 14px",
              }}
            >
              {insightsError ? (
                <div style={{ color: "var(--danger-text)", fontSize: 14 }}>{insightsError}</div>
              ) : visibleInsights.length === 0 ? (
                <div style={{ color: "#7c5cbf", fontSize: 14 }}>
                  No writing prompts available for this project.
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 14, color: "#7c5cbf", marginBottom: 10, lineHeight: 1.5 }}>
                    These prompts are based on your project's data. They are intended to help guide you to create or modify the project's bullet points.
                  </div>
                  <div style={{ display: "grid", gap: 7 }}>
                    {visibleInsights.map((message, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: "flex",
                          gap: 8,
                          alignItems: "flex-start",
                          padding: "8px 10px",
                          borderRadius: 8,
                          border: "1px solid #ddd6fe",
                          background: "#f0eeff",
                        }}
                      >
                        <span style={{ color: "#7c3aed", flexShrink: 0, fontSize: 14, lineHeight: 1.6 }}>✦</span>
                        <span style={{ flex: 1, fontSize: 14, color: "#4c1d95", lineHeight: 1.6 }}>{message}</span>
                        <button
                          onClick={() => handleDismissInsight(message, idx)}
                          title="Dismiss this prompt"
                          style={{
                            padding: "1px 6px",
                            borderRadius: 5,
                            border: "1px solid var(--border)",
                            background: "transparent",
                            color: "var(--text-muted)",
                            fontSize: 15,
                            cursor: "pointer",
                            flexShrink: 0,
                            fontFamily: "inherit",
                            lineHeight: 1,
                          }}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

// ─── Education Section ────────────────────────────────────────────────────────

type EntryDraft = { title: string; start: string; end: string; description: string };

function EntryListSection({
  label,
  entries,
  emptyText,
  titlePlaceholder,
  onSave,
}: {
  label: string;
  entries: import("../api/apiClient").EducationEntry[];
  emptyText: string;
  titlePlaceholder: string;
  onSave: (draft: EntryDraft[]) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<EntryDraft[]>([]);

  function startEditing() {
    setDraft(entries.map((e) => ({ title: e.title ?? "", start: e.start ?? "", end: e.end ?? "", description: (e.description ?? []).join("\n") })));
    setEditing(true);
  }

  function updateField(i: number, field: keyof EntryDraft, value: string) {
    setDraft((d) => d.map((e, idx) => (idx === i ? { ...e, [field]: value } : e)));
  }

  function removeEntry(i: number) {
    setDraft((d) => d.filter((_, idx) => idx !== i));
  }

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(draft.filter((e) => e.title.trim()));
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  const inputBase: React.CSSProperties = {
    padding: "7px 10px",
    borderRadius: 8,
    border: "1px solid var(--border-strong)",
    background: "var(--bg-input)",
    color: "var(--text-primary)",
    fontSize: 13,
    fontFamily: "inherit",
    outline: "none",
  };

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, padding: "16px 20px", background: "var(--bg-surface)", marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <span style={SECTION_LABEL}>{label}</span>
        {!editing && (
          <button onClick={startEditing} style={{ padding: "4px 10px", borderRadius: 7, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", cursor: "pointer", fontSize: 12 }}>
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {draft.map((entry, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", gap: 6, background: "var(--bg-surface-deep)", borderRadius: 10, padding: "10px 12px", position: "relative" }}>
              <button
                onClick={() => removeEntry(i)}
                style={{ position: "absolute", top: 8, right: 8, padding: "2px 7px", borderRadius: 6, border: "1px solid var(--danger-bg-strong)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", fontSize: 12 }}
              >✕</button>
              <input
                style={{ ...inputBase, width: "calc(100% - 44px)" }}
                value={entry.title}
                onChange={(e) => updateField(i, "title", e.target.value)}
                placeholder={titlePlaceholder}
              />
              <div style={{ display: "flex", gap: 8 }}>
                <input style={{ ...inputBase, flex: 1 }} value={entry.start} onChange={(e) => updateField(i, "start", e.target.value)} placeholder="Start (e.g. September 2022)" />
                <input style={{ ...inputBase, flex: 1 }} value={entry.end} onChange={(e) => updateField(i, "end", e.target.value)} placeholder="End (e.g. April 2026)" />
              </div>
              <textarea
                style={{ ...inputBase, width: "100%", minHeight: 72, resize: "vertical", boxSizing: "border-box" }}
                value={entry.description}
                onChange={(e) => updateField(i, "description", e.target.value)}
                placeholder={"Add bullet points (one per line)"}
              />
            </div>
          ))}
          <button
            onClick={() => setDraft((d) => [...d, { title: "", start: "", end: "", description: "" }])}
            style={{ alignSelf: "flex-start", padding: "5px 12px", borderRadius: 7, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", cursor: "pointer", fontSize: 12, marginTop: 2 }}
          >+ Add Entry</button>
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button onClick={() => setEditing(false)} disabled={saving} style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", cursor: "pointer", fontSize: 13, opacity: saving ? 0.6 : 1 }}>Cancel</button>
            <button onClick={handleSave} disabled={saving} style={{ padding: "6px 14px", borderRadius: 8, border: "none", background: "var(--btn-primary)", color: saving ? "var(--text-muted)" : "#fff", cursor: saving ? "not-allowed" : "pointer", fontSize: 13, opacity: saving ? 0.6 : 1 }}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {entries.length === 0 ? (
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>{emptyText}</span>
          ) : (
            entries.map((entry, i) => {
              const dateRange = [entry.start, entry.end].filter(Boolean).join(" \u2013 ");
              return (
                <div key={i} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontSize: 13, color: "var(--text-primary)" }}>
                    <span style={{ fontWeight: 500 }}>{entry.title}</span>
                    {dateRange && <span style={{ color: "var(--text-muted)", fontSize: 12, marginLeft: 16, whiteSpace: "nowrap" }}>{dateRange}</span>}
                  </div>
                  {(entry.description ?? []).length > 0 && (
                    <ul style={{ margin: "2px 0 0 0", paddingLeft: 18, display: "flex", flexDirection: "column", gap: 1 }}>
                      {(entry.description ?? []).map((b, j) => (
                        <li key={j} style={{ fontSize: 12, color: "var(--text-muted)" }}>{b}</li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

function EducationSection({
  resumeId,
  education,
  onUpdated,
  onError,
}: {
  resumeId: number;
  education: import("../api/apiClient").EducationEntry[];
  onUpdated: (res: import("../api/apiClient").ResumeResponse) => void;
  onError: (msg: string) => void;
}) {
  return (
    <EntryListSection
      label="Education"
      entries={education}
      emptyText="No education entries. Click Edit to add."
      titlePlaceholder="e.g. BSc Computer Science, University of British Columbia"
      onSave={async (draft) => {
        try {
          const res = await api.editResumeEducation(resumeId, {
            education: draft.map((e) => ({ title: e.title.trim(), start: e.start.trim() || null, end: e.end.trim() || null, description: e.description.split("\n").map((b) => b.trim()).filter(Boolean) })),
          });
          onUpdated(res);
        } catch (e: any) {
          onError(e?.message ?? "Failed to save education.");
          throw e;
        }
      }}
    />
  );
}

// ─── Awards Section ───────────────────────────────────────────────────────────

function AwardsSection({
  resumeId,
  awards,
  onUpdated,
  onError,
}: {
  resumeId: number;
  awards: import("../api/apiClient").AwardEntry[];
  onUpdated: (res: import("../api/apiClient").ResumeResponse) => void;
  onError: (msg: string) => void;
}) {
  return (
    <EntryListSection
      label="Awards"
      entries={awards}
      emptyText="No awards entries. Click Edit to add."
      titlePlaceholder="e.g. Dean's List"
      onSave={async (draft) => {
        try {
          const res = await api.editResumeAwards(resumeId, {
            awards: draft.map((e) => ({ title: e.title.trim(), start: e.start.trim() || null, end: e.end.trim() || null, description: e.description.split("\n").map((b) => b.trim()).filter(Boolean) })),
          });
          onUpdated(res);
        } catch (e: any) {
          onError(e?.message ?? "Failed to save awards.");
          throw e;
        }
      }}
    />
  );
}

// ─── Header Section ───────────────────────────────────────────────────────────

type HeaderDraft = {
  name: string;
  location: string;
  email: string;
  github: string;
  linkedin: string;
};

function HeaderSection({
  resumeId,
  resume,
  onUpdated,
  onError,
}: {
  resumeId: number;
  resume: import("../api/apiClient").ResumeResponse;
  onUpdated: (res: import("../api/apiClient").ResumeResponse) => void;
  onError: (msg: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<HeaderDraft>({
    name: resume.name ?? "",
    location: resume.location ?? "",
    email: resume.email ?? "",
    github: resume.github ?? "",
    linkedin: resume.linkedin ?? "",
  });

  function startEditing() {
    setDraft({
      name: resume.name ?? "",
      location: resume.location ?? "",
      email: resume.email ?? "",
      github: resume.github ?? "",
      linkedin: resume.linkedin ?? "",
    });
    setEditing(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const res = await api.editResumeHeader(resumeId, {
        name: draft.name.trim() || null,
        location: draft.location.trim() || null,
        email: draft.email.trim() || null,
        github_username: draft.github.trim() || null,
        linkedin: draft.linkedin.trim() || null,
      });
      onUpdated(res);
      setEditing(false);
    } catch (e: any) {
      onError(e?.message ?? "Failed to save header.");
    } finally {
      setSaving(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "7px 10px",
    borderRadius: 8,
    border: "1px solid var(--border-strong)",
    background: "var(--bg-input)",
    color: "var(--text-primary)",
    fontSize: 13,
    fontFamily: "inherit",
    outline: "none",
    boxSizing: "border-box",
  };

  const rowStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 11,
    color: "var(--text-muted)",
    fontWeight: 600,
    letterSpacing: "0.05em",
    textTransform: "uppercase",
  };

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "16px 20px",
        background: "var(--bg-surface)",
        marginBottom: 16,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <span style={SECTION_LABEL}>Header</span>
        {!editing && (
          <button
            onClick={startEditing}
            style={{
              padding: "4px 10px",
              borderRadius: 7,
              border: "1px solid var(--border)",
              background: "transparent",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={rowStyle}>
            <span style={labelStyle}>Full Name</span>
            <input
              style={inputStyle}
              value={draft.name}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
              placeholder="e.g. Paul Atreides"
            />
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>Location</span>
            <input
              style={inputStyle}
              value={draft.location}
              onChange={(e) => setDraft((d) => ({ ...d, location: e.target.value }))}
              placeholder="e.g. Vancouver, BC"
            />
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>Email</span>
            <input
              style={inputStyle}
              value={draft.email}
              onChange={(e) => setDraft((d) => ({ ...d, email: e.target.value }))}
              placeholder="e.g. paulatreides@email.com"
            />
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>LinkedIn</span>
            <input
              style={inputStyle}
              value={draft.linkedin}
              onChange={(e) => setDraft((d) => ({ ...d, linkedin: e.target.value }))}
              placeholder="https://www.linkedin.com/in/your-profile"
            />
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>GitHub</span>
            <input
              style={inputStyle}
              value={draft.github}
              onChange={(e) => setDraft((d) => ({ ...d, github: e.target.value }))}
              placeholder="Your GitHub Username"
            />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button
              onClick={() => setEditing(false)}
              disabled={saving}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "transparent",
                color: "var(--text-muted)",
                cursor: "pointer",
                fontSize: 13,
                opacity: saving ? 0.6 : 1,
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                border: "none",
                background: "var(--btn-primary)",
                color: saving ? "var(--text-muted)" : "#fff",
                cursor: saving ? "not-allowed" : "pointer",
                fontSize: 13,
                opacity: saving ? 0.6 : 1,
              }}
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14 }}>
          <div><span style={{ color: "var(--text-muted)", marginRight: 8 }}>Name</span><span style={{ color: resume.name ? "var(--text-primary)" : "var(--text-muted)" }}>{resume.name || "—"}</span></div>
          <div><span style={{ color: "var(--text-muted)", marginRight: 8 }}>Location</span><span style={{ color: resume.location ? "var(--text-primary)" : "var(--text-muted)" }}>{resume.location || "—"}</span></div>
          <div><span style={{ color: "var(--text-muted)", marginRight: 8 }}>Email</span><span style={{ color: resume.email ? "var(--text-primary)" : "var(--text-muted)" }}>{resume.email || "—"}</span></div>
          <div><span style={{ color: "var(--text-muted)", marginRight: 8 }}>LinkedIn</span><span style={{ color: resume.linkedin ? "var(--text-primary)" : "var(--text-muted)" }}>{resume.linkedin || "—"}</span></div>
          <div><span style={{ color: "var(--text-muted)", marginRight: 8 }}>GitHub</span><span style={{ color: resume.github ? "var(--text-primary)" : "var(--text-muted)" }}>{resume.github || "—"}</span></div>
        </div>
      )}
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

  // Export
  const [exporting, setExporting] = useState(false);
  const [exportingDocx, setExportingDocx] = useState(false);

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
      <div style={{ padding: 24, paddingTop: 40 }}>
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 20,
            background: "var(--bg-surface)",
            color: "var(--text-secondary)",
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
      <div style={{ padding: 24, paddingTop: 40 }}>
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 28,
            background: "var(--bg-surface)",
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No resume found</div>
          <div style={{ color: "var(--text-secondary)", marginBottom: 20, fontSize: 14 }}>
            {error ?? "Create a resume from the resumes page."}
          </div>
          <Link
            to={backTo}
            style={{
              display: "inline-block",
              padding: "9px 16px",
              borderRadius: 9,
              border: "1px solid var(--border)",
              background: "var(--bg-surface-deep)",
              color: "var(--text-primary)",
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
    <div style={{ padding: 24, paddingTop: 40 }}>
      {/* Back */}
      <Link to={backTo} style={{ color: "var(--accent)", textDecoration: "none", fontSize: 14 }}>
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
                  border: "1px solid var(--border)",
                  background: "var(--bg-input)",
                  color: "var(--text-primary)",
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
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: "var(--text-primary)",
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
                  border: "none",
                  background: savingTitle ? "var(--bg-surface-deep)" : "var(--btn-primary)",
                  color: savingTitle ? "var(--text-muted)" : "#fff",
                  cursor: savingTitle ? "not-allowed" : "pointer",
                  fontSize: 14,
                  fontWeight: 600,
                  opacity: savingTitle ? 0.6 : 1,
                }}
              >
                Apply
              </button>
            </div>
          ) : (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <h1 style={{ margin: 0, fontSize: 28 }}>{displayTitle}</h1>
                <button
                  onClick={() => setEditingTitle(true)}
                  style={{
                    padding: "4px 8px",
                    borderRadius: 8,
                    border: "1px solid var(--btn-primary)",
                    background: "transparent",
                    color: "var(--btn-primary)",
                    cursor: "pointer",
                    fontSize: 14,
                    fontWeight: 500,
                  }}
                >
                  Edit
                </button>
              </div>
              {resume.created_at && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                  Created {new Date(resume.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}
                </div>
              )}
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
              border: "none",
              background: savingTitle ? "var(--bg-surface-deep)" : "var(--btn-primary)",
              color: savingTitle ? "var(--text-muted)" : "#fff",
              fontWeight: 600,
              cursor: savingTitle ? "not-allowed" : "pointer",
              fontSize: 14,
              opacity: savingTitle ? 0.6 : 1,
            }}
          >
            {savingTitle ? "Saving..." : "Save"}
          </button>

          <button
            onClick={async () => {
              setExporting(true);
              try {
                await api.exportResumePdf(
                  Number(resumeId),
                  `${resume.title || `resume_${resume.id}`}.pdf`
                );
              } catch (e: any) {
                setError(e?.message ?? "Export failed.");
              } finally {
                setExporting(false);
              }
            }}
            disabled={exporting}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--btn-primary)",
              borderRadius: 10,
              color: exporting ? "var(--text-muted)" : "var(--btn-primary)",
              fontWeight: 500,
              cursor: exporting ? "not-allowed" : "pointer",
              opacity: exporting ? 0.6 : 1,
            }}
          >
            {exporting ? "Exporting..." : "Export PDF"}
          </button>

          <button
            onClick={async () => {
              setExportingDocx(true);
              try {
                await api.exportResumeDocx(
                  Number(resumeId),
                  `${resume.title || `resume_${resume.id}`}.docx`
                );
              } catch (e: any) {
                setError(e?.message ?? "Export failed.");
              } finally {
                setExportingDocx(false);
              }
            }}
            disabled={exportingDocx}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--btn-primary)",
              borderRadius: 10,
              color: exportingDocx ? "var(--text-muted)" : "var(--btn-primary)",
              fontWeight: 500,
              cursor: exportingDocx ? "not-allowed" : "pointer",
              opacity: exportingDocx ? 0.6 : 1,
            }}
          >
            {exportingDocx ? "Exporting..." : "Export Word"}
          </button>

          <button
            onClick={() => setShowDeleteConfirm(true)}
            style={{
              padding: "10px 14px",
              background: "#dc2626",
              border: "none",
              borderRadius: 10,
              color: "#fff",
              fontWeight: 600,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Delete
          </button>
        </div>
      </div>

      {saveError && (
        <div style={{ color: "var(--danger-text)", fontSize: 14, marginBottom: 14 }}>{saveError}</div>
      )}

      {error && <Toast message={error} type="error" />}
      {success && <Toast message={success} type="success" />}

      {/* Page overflow warning */}
      {estimateResumeLines(resume) > LINES_PER_PAGE && (
        <div
          style={{
            border: "1px solid #d97706",
            borderRadius: 10,
            padding: "11px 16px",
            background: "#fffbeb",
            color: "#92400e",
            fontSize: 14,
            marginBottom: 14,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <WarningAmberIcon style={{ fontSize: 20 }} />
          <span>
            Your resume may exceed one page when exported. Consider reducing the
            number of bullet points or projects to keep it concise.
          </span>
        </div>
      )}

      {/* Header */}
      <HeaderSection
        resumeId={resume.id!}
        resume={resume}
        onUpdated={(res) => {
          setResume(res);
          showSuccess("Header saved.");
        }}
        onError={(msg) => setError(msg)}
      />

      {/* Education */}
      <EducationSection
        resumeId={resume.id!}
        education={resume.education ?? []}
        onUpdated={(res) => {
          setResume(res);
          showSuccess("Education saved.");
        }}
        onError={(msg) => setError(msg)}
      />

      {/* Awards */}
      <AwardsSection
        resumeId={resume.id!}
        awards={resume.awards ?? []}
        onUpdated={(res) => {
          setResume(res);
          showSuccess("Awards saved.");
        }}
        onError={(msg) => setError(msg)}
      />

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
          border: "1px solid var(--border)",
          borderRadius: 14,
          padding: "16px 20px",
          background: "var(--bg-surface)",
        }}
      >
        <span style={SECTION_LABEL}>Projects</span>

        {!resume.items || resume.items.length === 0 ? (
          <div style={{ fontSize: 15, color: "var(--text-secondary)" }}>No projects in this resume.</div>
        ) : (
          <div style={{ display: "grid", gap: 14 }}>
            {resume.items
              .map((item, originalIndex) => ({ item, originalIndex }))
              .sort((a, b) => {
                const aDate = a.item.end_date || a.item.start_date || "";
                const bDate = b.item.end_date || b.item.start_date || "";
                return bDate.localeCompare(aDate);
              })
              .map(({ item, originalIndex }) => (
              <ItemCard
                key={`${item.title}-${originalIndex}`}
                resumeId={resume.id!}
                item={item}
                itemIndex={originalIndex}
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
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: 16,
              padding: 24,
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Delete Resume</h2>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Are you sure you want to delete{" "}
              <strong>"{displayTitle}"</strong>? This will permanently remove
              the resume and all its content. This cannot be undone.
            </p>

            {deleteError && (
              <div
                style={{
                  color: "var(--danger-text)",
                  fontSize: 14,
                  marginBottom: 16,
                  padding: "8px 12px",
                  background: "var(--danger-bg)",
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
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: deleting ? "var(--text-muted)" : "var(--text-primary)",
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
                  border: "none",
                  background: deleting ? "#b91c1c" : "#dc2626",
                  color: "#fff",
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
