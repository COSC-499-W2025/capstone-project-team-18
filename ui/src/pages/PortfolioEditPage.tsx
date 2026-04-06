import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/apiClient";
import TextBlockEditor from "../components/blocks/TextBlockEditor";
import TextListBlockEditor from "../components/blocks/TextListBlockEditor";
import ContributionMap from "../components/ContributionMap";
import SkillTimelineGraph from "../components/SkillTimelineGraph";
import { LanguageDonut } from "../components/LanguageDonut";

// ---- Types ----------------------------------------------------------------

type BlockMetadata = {
  last_generated_at?: string;
  last_user_edit_at?: string;
};

type Block = {
  tag: string;
  current_content: any;
  content_type: string;
  metadata: BlockMetadata;
};

type PortfolioSection = {
  id: string;
  title: string;
  order: number;
  block_order: string[];
  blocks_by_tag: Record<string, Block>;
};

type PortfolioCard = {
  project_name: string;
  summary: string;
  themes: string[];
  tones: string;
  tags: string[];
  skills: string[];
  frameworks: string[];
  languages?: Record<string, number>;
  is_showcase: boolean;
  collaboration_role?: string;
  title_override?: string | null;
  summary_override?: string | null;
  tags_override?: string[] | null;
};

type Portfolio = {
  title: string;
  metadata: {
    creation_time: string;
    last_updated_at: string;
    project_ids_include: string[];
  };
  sections: PortfolioSection[];
  project_cards: PortfolioCard[];
};

type BlockEditEntry = {
  draft: string | string[];
  saving: boolean;
  error: string | null;
};

// ---- Helpers ---------------------------------------------------------------

const CODING_LANGUAGE_DISPLAY: Record<string, string> = {
  PYTHON: "Python", JAVASCRIPT: "JavaScript", TYPESCRIPT: "TypeScript",
  JAVA: "Java", CPP: "C++", C: "C", CSHARP: "C#", PHP: "PHP",
  RUBY: "Ruby", SWIFT: "Swift", GO: "Go", RUST: "Rust",
  HTML: "HTML", CSS: "CSS", SQL: "SQL", SHELL: "Shell", R: "R",
};

function parseCardLanguageName(key: string): string {
  if (key.startsWith("__enum__:")) return key.split(":").pop() ?? key;
  const dotIdx = key.lastIndexOf(".");
  if (dotIdx >= 0) {
    const member = key.slice(dotIdx + 1);
    return CODING_LANGUAGE_DISPLAY[member] ?? member;
  }
  return key;
}

function aggregatePortfolioLanguages(cards: PortfolioCard[]): Array<{ lang: string; ratio: number }> {
  const totals: Record<string, number> = {};
  for (const card of cards) {
    if (!card.languages) continue;
    for (const [key, ratio] of Object.entries(card.languages)) {
      const lang = parseCardLanguageName(key);
      totals[lang] = (totals[lang] ?? 0) + ratio;
    }
  }
  return Object.entries(totals)
    .map(([lang, ratio]) => ({ lang, ratio }))
    .filter(({ ratio }) => ratio > 0)
    .sort((a, b) => b.ratio - a.ratio);
}

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      });
}

function pillStyle(color?: string) {
  return {
    fontSize: 11,
    color: color ?? "var(--text-primary)",
    border: `1px solid ${color ? color + "44" : "var(--border)"}`,
    borderRadius: 999,
    padding: "3px 8px",
    whiteSpace: "nowrap" as const,
    background: color ? color + "11" : "transparent",
  };
}

// ---- Shared card field styles ---------------------------------------------

const sectionLabel: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text-muted)",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  display: "block",
  marginBottom: 8,
};

const fieldInput: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-input)",
  color: "var(--text-primary)",
  fontSize: 13,
  boxSizing: "border-box",
  outline: "none",
};

// ---- PillField sub-component -----------------------------------------------

type PillFieldProps = {
  label: string;
  pills: string[];
  inputValue: string;
  pillColor: string;
  borderColor: string;
  bgColor: string;
  placeholder: string;
  onRemove: (value: string) => void;
  onInputChange: (value: string) => void;
  onAdd: (value: string) => void;
};

function PillField({
  label,
  pills,
  inputValue,
  pillColor,
  borderColor,
  bgColor,
  placeholder,
  onRemove,
  onInputChange,
  onAdd,
}: PillFieldProps) {
  return (
    <div>
      <div style={sectionLabel}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
        {pills.map((p) => (
          <span
            key={p}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: 12,
              color: pillColor,
              border: `1px solid ${borderColor}`,
              borderRadius: 999,
              padding: "3px 10px",
              background: bgColor,
            }}
          >
            {p}
            <button
              onClick={() => onRemove(p)}
              style={{ background: "transparent", border: "none", color: pillColor + "99", cursor: "pointer", fontSize: 14, lineHeight: 1, padding: 0 }}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onAdd(inputValue.trim());
            }
          }}
          placeholder={placeholder}
          style={{ flex: 1, padding: "6px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-input)", color: "var(--text-primary)", fontSize: 12, outline: "none" }}
        />
        <button
          onClick={() => onAdd(inputValue.trim())}
          style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", cursor: "pointer", fontSize: 12 }}
        >
          + Add
        </button>
      </div>
    </div>
  );
}

// ---- Component ------------------------------------------------------------

export default function PortfolioEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const backTo: string = (location.state as any)?.from ?? "/portfolios";
  const backLabel = backTo === "/" ? "← Back to Dashboard" : "← Back to Portfolios";

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Title editing
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [prevTitleDraft, setPrevTitleDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [savingTitle, setSavingTitle] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Action states
  const [githubConnected, setGithubConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [exportedPagesUrl, setExportedPagesUrl] = useState<string | null>(null);
  const [showDeployConfirm, setShowDeployConfirm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showRefreshConfirm, setShowRefreshConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // A toast to notify the user that their portfolio has been deployed
  useEffect(() => {
    if (!exportedPagesUrl) return;
    const timer = setTimeout(() => setExportedPagesUrl(null), 6000); // clears after 6 seconds
    return () => clearTimeout(timer);
  }, [exportedPagesUrl]);


  // Per-card edit state
  const [cardEdits, setCardEdits] = useState<
    Record<
      string,
      {
        // User-override fields (preserved on portfolio refresh)
        titleDraft: string;
        summaryDraft: string;
        tagsDraft: string[];
        // Directly-updated fields (overwritten on portfolio refresh)
        skillsDraft: string[];
        themesDraft: string[];
        toneDraft: string;
        frameworksDraft: string[];
        // Inline add inputs
        newSkillInput: string;
        newThemeInput: string;
        newTagInput: string;
        newFrameworkInput: string;
        // UI state
        saving: boolean;
        error: string | null;
        showEditModal: boolean;
        showConfirmModal: boolean;
        showUnsavedWarning: boolean;
      }
    >
  >({});

  // Per-block edit state: { ["sectionId::blockTag"]: { draft, saving, error } }
  const [blockEdits, setBlockEdits] = useState<Record<string, BlockEditEntry>>({});

  // Contribution map state
  const [contributionData, setContributionData] = useState<{
    personal_timeline: Record<string, number>;
    total_timeline: Record<string, number>;
  } | null>(null);
  const [skillTimelineData, setSkillTimelineData] = useState<
    Record<string, Record<string, number>>
  >({});
  const [skillTimelineRange, setSkillTimelineRange] = useState<{
    startDate: string | null;
    endDate: string | null;
  }>({
    startDate: null,
    endDate: null,
  });
  const [contributionLoading, setContributionLoading] = useState(false);
  const [languageBreakdown, setLanguageBreakdown] = useState<Array<{ lang: string; ratio: number }>>([]);

  // ---- Load ----------------------------------------------------------------

  useEffect(() => {
    if (!id || isNaN(Number(id))) {
      navigate("/portfolios", { replace: true });
      return;
    }
    loadPortfolio();
  }, [id]);

  async function loadPortfolio() {
    setLoading(true);
    setError(null);
    try {
      const [data, userConfig] = await Promise.all([
        api.getPortfolio(id!) as Promise<Portfolio>,
        api.getUserConfig(),
      ]);
      setPortfolio(data);
      setTitleDraft(data.title);
      initCardEdits(data.project_cards);
      initBlockEdits(data.sections);
      setLanguageBreakdown(aggregatePortfolioLanguages(data.project_cards));

      try {
        setContributionLoading(true);
        const projectNames = data.project_cards.map((c) => c.project_name);
        const personal_timeline: Record<string, number> = {};
        const total_timeline: Record<string, number> = {};
        const skill_timeline: Record<string, Record<string, number>> = {};
        let earliestProjectStartTs: number | null = null;
        let latestProjectEndTs: number | null = null;
        const toIsoDate = (value: number | null) =>
          value === null ? null : new globalThis.Date(value).toISOString().slice(0, 10);

        const updateTimelineRange = (value: unknown, isStart: boolean) => {
          if (typeof value !== "string") return;
          const parsed = new globalThis.Date(value);
          if (Number.isNaN(parsed.getTime())) return;
          const parsedTs = parsed.getTime();

          if (isStart) {
            if (earliestProjectStartTs === null || parsedTs < earliestProjectStartTs) {
              earliestProjectStartTs = parsedTs;
            }
            return;
          }

          if (latestProjectEndTs === null || parsedTs > latestProjectEndTs) {
            latestProjectEndTs = parsedTs;
          }
        };

        const projectResults = await Promise.all(
          projectNames.map((projectName) =>
            api
              .getProject(projectName)
              .then((projectData) => ({ projectName, projectData }))
              .catch((e: any) => ({ projectName, error: e }))
          )
        );

        for (const result of projectResults) {
          const { projectName } = result as { projectName: string };

          if ("error" in result) {
            const e = (result as { projectName: string; error: any }).error;
            console.warn(`Failed to load contribution data for ${projectName}:`, e?.message);
            continue;
          }

          const projectData = (result as { projectName: string; projectData: any }).projectData;
          const statistic = projectData?.statistic || {};
          updateTimelineRange(statistic.PROJECT_START_DATE, true);
          updateTimelineRange(statistic.PROJECT_END_DATE, false);

          // Extract contribution timelines from project statistics
          const personalTimeline = statistic.COMMIT_ACTIVITY_TIMELINE || {};
          const totalTimeline = statistic.TOTAL_COMMIT_ACTIVITY_TIMELINE || {};
          const projectSkillActivity = statistic.PROJECT_SKILL_ACTIVITY || {};

          // Merge into aggregate timelines
          for (const [date, count] of Object.entries(personalTimeline)) {
            personal_timeline[date] = (personal_timeline[date] || 0) + (count as number);
          }
          for (const [date, count] of Object.entries(totalTimeline)) {
            total_timeline[date] = (total_timeline[date] || 0) + (count as number);
          }

          // Merge PROJECT_SKILL_ACTIVITY across all projects.
          // Expected shape: { "Skill": ["YYYY-MM-DD", ...] }
          for (const [skill, dates] of Object.entries(projectSkillActivity)) {
            if (!Array.isArray(dates)) continue;
            if (!skill_timeline[skill]) {
              skill_timeline[skill] = {};
            }
            for (const dateValue of dates) {
              if (typeof dateValue !== "string") continue;
              skill_timeline[skill][dateValue] =
                (skill_timeline[skill][dateValue] || 0) + 1;
            }
          }
        }

        setContributionData({
          personal_timeline,
          total_timeline,
        });
        setSkillTimelineData(skill_timeline);
        setSkillTimelineRange({
          startDate: toIsoDate(earliestProjectStartTs),
          endDate: toIsoDate(latestProjectEndTs),
        });
      } catch (e: any) {
        // Silently fail contribution loading so it doesn't block the page
        console.warn("Failed to load contribution map:", e?.message);
        setContributionData(null);
        setSkillTimelineData({});
        setSkillTimelineRange({
          startDate: null,
          endDate: null,
        });
      } finally {
        setContributionLoading(false);
      }
      setGithubConnected(Boolean(userConfig?.github_connected));
    } catch (e: any) {
      setError(e?.message ?? "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  }

  function initCardEdits(cards: PortfolioCard[]) {
    const edits: typeof cardEdits = {};
    for (const c of cards) {
      edits[c.project_name] = {
        titleDraft: c.title_override ?? c.project_name,
        summaryDraft: c.summary_override ?? c.summary ?? "",
        tagsDraft: c.tags_override ?? c.tags ?? [],
        skillsDraft: c.skills ?? [],
        themesDraft: c.themes ?? [],
        toneDraft: c.tones ?? "",
        frameworksDraft: c.frameworks ?? [],
        newSkillInput: "",
        newThemeInput: "",
        newTagInput: "",
        newFrameworkInput: "",
        saving: false,
        error: null,
        showEditModal: false,
        showConfirmModal: false,
        showUnsavedWarning: false,
      };
    }
    setCardEdits(edits);
  }

  function updateCard(
    projectName: string,
    update: Partial<(typeof cardEdits)[string]>
  ) {
    setCardEdits((prev) => ({
      ...prev,
      [projectName]: { ...prev[projectName], ...update },
    }));
  }

  function initBlockEdits(sections: PortfolioSection[]) {
    const edits: Record<string, BlockEditEntry> = {};
    for (const sec of sections) {
      for (const tag of sec.block_order) {
        const block = sec.blocks_by_tag[tag];
        if (!block) continue;
        const key = `${sec.id}::${tag}`;
        const contentType =
          block.content_type ?? block.current_content?.content_type ?? "";
        let draft: string | string[];
        if (contentType === "TextList") {
          const raw = block.current_content;
          if (Array.isArray(raw)) {
            draft = raw as string[];
          } else if (raw && Array.isArray(raw.items)) {
            draft = raw.items as string[];
          } else {
            draft = [];
          }
        } else {
          const raw = block.current_content;
          if (typeof raw === "string") {
            draft = raw;
          } else if (raw?.text != null) {
            draft = raw.text as string;
          } else if (raw != null) {
            draft = JSON.stringify(raw, null, 2);
          } else {
            draft = "";
          }
        }
        edits[key] = { draft, saving: false, error: null };
      }
    }
    setBlockEdits(edits);
  }

  // ---- Actions -------------------------------------------------------------

  async function handleSave() {
    if (!portfolio) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api.editPortfolio(id!, { title: titleDraft });
      setEditingTitle(false);
      await loadPortfolio();
    } catch (e: any) {
      setSaveError(e?.message ?? "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveTitle() {
    if (!portfolio) return;
    setSavingTitle(true);
    setSaveError(null);
    try {
      await api.editPortfolio(id!, { title: titleDraft });
      setEditingTitle(false);
      await loadPortfolio();
    } catch (e: any) {
      setSaveError(e?.message ?? "Failed to save.");
    } finally {
      setSavingTitle(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await api.refreshPortfolio(id!);
      await loadPortfolio();
    } catch (e: any) {
      setError(e?.message ?? "Failed to refresh.");
    } finally {
      setRefreshing(false);
    }
  }

  async function handleExport() {
    setShowDeployConfirm(false);
    setDeploying(true);
    setExportedPagesUrl(null);
    let objectUrl: string | null = null;
    try {
      const result = await api.exportPortfolio(id!);
      if (result instanceof Blob) {
        objectUrl = URL.createObjectURL(result);
        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = `portfolio_${id}.zip`;
        a.click();
      } else {
        setExportedPagesUrl(result.pagesUrl);
      }
    } catch (e: any) {
      setError(e?.message ?? "Failed to export.");
    } finally {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setDeploying(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deletePortfolio(id!);
      navigate("/portfolios");
    } catch (e: any) {
      setDeleteError(e?.message ?? "Failed to delete.");
      setDeleting(false);
    }
  }

  async function handleToggleShowcase(projectName: string) {
    if (!portfolio) return;
    const card = portfolio.project_cards.find(
      (c) => c.project_name === projectName
    );
    if (!card) return;
    const newVal = !card.is_showcase;
    // Optimistic update
    setPortfolio((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        project_cards: prev.project_cards.map((c) =>
          c.project_name === projectName ? { ...c, is_showcase: newVal } : c
        ),
      };
    });
    try {
      await api.setPortfolioCardShowcase(id!, projectName, newVal);
    } catch (e: any) {
      // Roll back
      setPortfolio((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          project_cards: prev.project_cards.map((c) =>
            c.project_name === projectName
              ? { ...c, is_showcase: !newVal }
              : c
          ),
        };
      });
    }
  }

  function isCardDirty(card: PortfolioCard, edit: (typeof cardEdits)[string]): boolean {
    const arrEq = (a: string[], b: string[]) =>
      JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
    return (
      edit.titleDraft !== (card.title_override ?? card.project_name) ||
      edit.summaryDraft !== (card.summary_override ?? card.summary ?? "") ||
      !arrEq(edit.tagsDraft, card.tags_override ?? card.tags ?? []) ||
      !arrEq(edit.skillsDraft, card.skills ?? []) ||
      !arrEq(edit.themesDraft, card.themes ?? []) ||
      edit.toneDraft !== (card.tones ?? "") ||
      !arrEq(edit.frameworksDraft, card.frameworks ?? [])
    );
  }

  function handleCloseEditModal(projectName: string) {
    const edit = cardEdits[projectName];
    const card = portfolio?.project_cards.find((c) => c.project_name === projectName);
    if (card && edit && isCardDirty(card, edit)) {
      updateCard(projectName, { showUnsavedWarning: true });
      return;
    }
    updateCard(projectName, { showEditModal: false });
  }

  async function handleSaveCard(projectName: string) {
    const edits = cardEdits[projectName];
    if (!edits) return;
    updateCard(projectName, { showConfirmModal: false, saving: true, error: null });
    try {
      await api.patchPortfolioCard(id!, projectName, {
        title_override: edits.titleDraft || null,
        summary_override: edits.summaryDraft || null,
        tags_override: edits.tagsDraft,   // always send array so empty [] clears tags instead of falling back to auto-generated
        skills: edits.skillsDraft,
        themes: edits.themesDraft,
        tones: edits.toneDraft,
        frameworks: edits.frameworksDraft,
      });
      updateCard(projectName, { saving: false, error: null, showEditModal: false, showConfirmModal: false });
    } catch (e: any) {
      updateCard(projectName, {
        saving: false,
        error: e?.message ?? "Failed to save card.",
      });
    }
  }

  async function handleSaveBlock(sectionId: string, blockTag: string, contentType: string) {
    const key = `${sectionId}::${blockTag}`;
    const edit = blockEdits[key];
    if (!edit) return;
    setBlockEdits((prev) => ({
      ...prev,
      [key]: { ...prev[key], saving: true, error: null },
    }));
    try {
      const payload =
        contentType === "TextList"
          ? { items: edit.draft as string[] }
          : { text: edit.draft as string };
      await api.editPortfolioBlock(id!, sectionId, blockTag, payload);
      setBlockEdits((prev) => ({
        ...prev,
        [key]: { ...prev[key], saving: false, error: null },
      }));
    } catch (e: any) {
      setBlockEdits((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          saving: false,
          error: e?.message ?? "Failed to save block.",
        },
      }));
    }
  }

  // ---- Render: Loading / Error --------------------------------------------

  if (loading) {
    return (
      <div style={{ padding: 24, paddingTop: 40 }}>
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 16,
            padding: 20,
            background: "var(--bg-surface)",
          }}
        >
          Loading portfolio...
        </div>
      </div>
    );
  }

  if (error && !portfolio) {
    return (
      <div style={{ padding: 24, paddingTop: 40 }}>
        <Link
          to={backTo}
          style={{ color: "var(--accent)", fontSize: 14, textDecoration: "none" }}
        >
          {backLabel}
        </Link>
        <div
          style={{
            marginTop: 16,
            border: "1px solid var(--danger-bg-strong)",
            borderRadius: 16,
            padding: 20,
            background: "var(--danger-bg)",
            color: "var(--danger-text)",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  if (!portfolio) return null;

  const sortedSections = [...portfolio.sections].sort(
    (a, b) => a.order - b.order
  );
  const sortedCards = portfolio.project_cards;

  // ---- Render: Main -------------------------------------------------------

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      {/* Back */}
      <Link
        to={backTo}
        style={{ color: "var(--accent)", fontSize: 14, textDecoration: "none" }}
      >
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
        }}
      >
        {/* Title + mode + dates */}
        <div>
          {editingTitle ? (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveTitle();
                  if (e.key === "Escape") { setTitleDraft(prevTitleDraft); setEditingTitle(false); }
                }}
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  padding: "6px 10px",
                  borderRadius: 10,
                  border: "1px solid var(--border)",
                  background: "var(--bg-input)",
                  color: "var(--text-primary)",
                  minWidth: 280,
                }}
                autoFocus
              />
              <button
                onClick={() => { setTitleDraft(prevTitleDraft); setEditingTitle(false); }}
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
                Back
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
                {savingTitle ? "Saving..." : "Apply"}
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ margin: 0, fontSize: 28 }}>{titleDraft}</h1>
              <button
                onClick={() => { setPrevTitleDraft(titleDraft); setEditingTitle(true); }}
                style={{
                  padding: "4px 8px",
                  borderRadius: 8,
                  border: "1px solid var(--btn-primary)",
                  background: "transparent",
                  color: "var(--btn-primary)",
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 500,
                }}
              >
                Edit
              </button>
            </div>
          )}

          <div
            style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 10 }}
          >
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Updated: {formatDate(portfolio.metadata.last_updated_at)}
            </span>
          </div>
        </div>

        {/* Action bar */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: "10px 14px",
              background: saving ? "var(--bg-surface-deep)" : "var(--btn-primary)",
              border: "none",
              borderRadius: 10,
              color: saving ? "var(--text-muted)" : "#fff",
              fontWeight: 600,
              cursor: saving ? "not-allowed" : "pointer",
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? "Saving..." : "Save"}
          </button>

          <button
            onClick={() => setShowRefreshConfirm(true)}
            disabled={refreshing}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--btn-primary)",
              borderRadius: 10,
              color: refreshing ? "var(--text-muted)" : "var(--btn-primary)",
              fontWeight: 500,
              cursor: refreshing ? "not-allowed" : "pointer",
              opacity: refreshing ? 0.6 : 1,
            }}
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>

          <button
            onClick={() => githubConnected ? setShowDeployConfirm(true) : handleExport()}
            disabled={deploying}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid var(--btn-primary)",
              borderRadius: 10,
              color: deploying ? "var(--text-muted)" : "var(--btn-primary)",
              fontWeight: 500,
              cursor: deploying ? "not-allowed" : "pointer",
              opacity: deploying ? 0.6 : 1,
            }}
          >
            {githubConnected && deploying ? "Deploying..." : githubConnected ? "Publish to GitHub" : "Download Website"}
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
            }}
          >
            Delete
          </button>
        </div>
      </div>

      {/* Save error */}
      {saveError && (
        <div style={{ color: "var(--danger-text)", fontSize: 14, marginTop: 10 }}>
          {saveError}
        </div>
      )}

      {/* General error (post-load) */}
      {error && (
        <div
          style={{
            marginTop: 16,
            color: "var(--danger-text)",
            fontSize: 14,
            border: "1px solid var(--danger-bg-strong)",
            borderRadius: 12,
            padding: 12,
            background: "var(--danger-bg)",
          }}
        >
          {error}
        </div>
      )}

      {contributionLoading && (
        <div style={{ marginTop: 16, color: "var(--text-muted)", fontSize: 13 }}>
          Loading activity graphs...
        </div>
      )}

      {/* GitHub Pages deployment success toast */}
      {exportedPagesUrl && (
        <div
          style={{
            position: "fixed",
            bottom: 28,
            right: 28,
            zIndex: 1100,
            fontSize: 14,
            border: "1px solid #b2dfb2",
            borderRadius: 12,
            padding: "14px 18px",
            background: "#f0faf0",
            color: "#155724",
            boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
            maxWidth: 420,
          }}
        >
          Portfolio deployed to GitHub Pages:{" "}
          <a
            href={exportedPagesUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "#155724" }}
          >
            {exportedPagesUrl}
          </a>
        </div>
      )}

      {/* ---- Narrative Sections ---- */}
      {sortedSections.length > 0 && (
        <div style={{ marginTop: 40 }}>


          <div style={{ display: "grid", gap: 24 }}>
            {sortedSections.map((section) => (
              <div
                key={section.id}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 16,
                  padding: 20,
                  background: "var(--bg-surface)",
                }}
              >
                <h3 style={{ marginTop: 0, marginBottom: 16 }}>
                  {section.title}
                </h3>

                <div style={{ display: "grid", gap: 16 }}>
                  {section.block_order.map((blockTag) => {
                    const block = section.blocks_by_tag[blockTag];
                    if (!block) return null;
                    const key = `${section.id}::${blockTag}`;
                    const edit = blockEdits[key];
                    if (!edit) return null;
                    const contentType =
                      block.content_type ??
                      block.current_content?.content_type ??
                      "";
                    const isText = contentType === "Text";
                    const isTextList = contentType === "TextList";

                    return (
                      <div key={blockTag}>
                        {isText && (
                          <TextBlockEditor
                            draft={edit.draft as string}
                            saving={edit.saving}
                            error={edit.error}
                            onChange={(value) =>
                              setBlockEdits((prev) => ({
                                ...prev,
                                [key]: { ...prev[key], draft: value },
                              }))
                            }
                            onSave={() =>
                              handleSaveBlock(section.id, blockTag, block.content_type)
                            }
                          />
                        )}

                        {isTextList && (
                          <TextListBlockEditor
                            draft={edit.draft as string[]}
                            saving={edit.saving}
                            error={edit.error}
                            onChange={(items) =>
                              setBlockEdits((prev) => ({
                                ...prev,
                                [key]: { ...prev[key], draft: items },
                              }))
                            }
                            onSave={() =>
                              handleSaveBlock(section.id, blockTag, block.content_type)
                            }
                          />
                        )}

                        {!isText && !isTextList && (
                          <pre
                            style={{
                              margin: 0,
                              padding: "8px 10px",
                              borderRadius: 8,
                              border: "1px solid var(--border)",
                              background: "#f0f0f0",
                              color: "var(--text-muted)",
                              fontSize: 12,
                              overflowX: "auto",
                              fontFamily: "monospace",
                              lineHeight: 1.5,
                            }}
                          >
                            {typeof edit.draft === "string"
                              ? edit.draft || "(empty)"
                              : JSON.stringify(edit.draft)}
                          </pre>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Figures ---- */}
      {(contributionLoading || contributionData || Object.keys(skillTimelineData).length > 0 || languageBreakdown.length > 0) && (
        <div style={{ marginTop: 40 }}>
          <h2 style={{ marginBottom: 16 }}>Figures</h2>

          {languageBreakdown.length > 0 && (
            <div
              style={{
                border: "1px solid var(--border)",
                borderRadius: 16,
                padding: 20,
                background: "var(--bg-surface)",
                marginBottom: 16,
              }}
            >
              <h3 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 600 }}>Language Breakdown</h3>
              <LanguageDonut langs={languageBreakdown} />
            </div>
          )}

          {contributionLoading && (
            <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
              Loading activity graphs...
            </div>
          )}

          {contributionData && (
            <div style={{ marginTop: 16 }}>
              <ContributionMap
                personalTimeline={contributionData.personal_timeline}
                totalTimeline={contributionData.total_timeline}
              />
            </div>
          )}

          {Object.keys(skillTimelineData).length > 0 && (
            <div style={{ marginTop: 24 }}>
              <SkillTimelineGraph data={skillTimelineData} range={skillTimelineRange} />
            </div>
          )}
        </div>
      )}


      {/* ---- Project Cards ---- */}
      <div style={{ marginTop: 40, paddingBottom: 80 }}>
        <h2 style={{ marginBottom: 16 }}>Projects</h2>

        {sortedCards.length === 0 && (
          <div
            style={{
              border: "1px solid var(--border)",
              borderRadius: 16,
              padding: 20,
              background: "var(--bg-surface)",
              color: "var(--text-muted)",
            }}
          >
            No project cards.
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(480px, 1fr))", gap: 8, alignItems: "start" }}>
          {sortedCards.map((card) => {
            const edit = cardEdits[card.project_name];
            if (!edit) return null;

            return (
              <div
                key={card.project_name}
                style={{
                  border: card.is_showcase ? "1px solid #b45309" : "1px solid var(--border)",
                  borderRadius: 14,
                  background: "var(--bg-surface)",
                  overflow: "hidden",
                }}
              >
                {/* ── Card row ── */}
                <div
                  onClick={() => updateCard(card.project_name, { showEditModal: true })}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "14px 18px",
                    gap: 12,
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                    <span style={{ fontWeight: 600, fontSize: 15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {edit.titleDraft || card.project_name}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleShowcase(card.project_name);
                      }}
                      style={{
                        padding: "4px 10px",
                        borderRadius: 999,
                        border: `1px solid ${card.is_showcase ? "#b45309" : "var(--border)"}`,
                        background: card.is_showcase ? "#fef3c7" : "transparent",
                        color: card.is_showcase ? "#92400e" : "var(--text-muted)",
                        cursor: "pointer",
                        fontSize: 12,
                        fontWeight: card.is_showcase ? 600 : 400,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {card.is_showcase ? "★ Showcased" : "☆ Showcase"}
                    </button>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                  </div>
                </div>

                {/* ── Edit Modal ── */}
                {edit.showEditModal && (
                  <div
                    onClick={() => handleCloseEditModal(card.project_name)}
                    style={{
                      position: "fixed",
                      inset: 0,
                      background: "rgba(0,0,0,0.72)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      zIndex: 1100,
                      padding: 24,
                    }}
                  >
                    <div
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        width: "100%",
                        maxWidth: "min(720px, 95vw)",
                        maxHeight: "90vh",
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 16,
                        boxShadow: "0 24px 64px rgba(0,0,0,0.55)",
                        display: "flex",
                        flexDirection: "column",
                        overflow: "hidden",
                      }}
                    >
                      {/* Modal header */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 24px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
                        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>
                          {edit.titleDraft || card.project_name}
                        </h2>
                        <button
                          onClick={() => handleCloseEditModal(card.project_name)}
                          style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 22, lineHeight: 1, padding: "2px 6px", borderRadius: 6 }}
                        >
                          ✕
                        </button>
                      </div>

                      {/* Modal scrollable body */}
                      <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: 20 }}>
                        {/* Title */}
                        <div>
                          <label style={sectionLabel}>Title</label>
                          <input
                            value={edit.titleDraft}
                            onChange={(e) => updateCard(card.project_name, { titleDraft: e.target.value })}
                            style={fieldInput}
                          />
                        </div>

                        {/* Summary */}
                        <div>
                          <label style={sectionLabel}>Summary</label>
                          <textarea
                            value={edit.summaryDraft}
                            onChange={(e) => updateCard(card.project_name, { summaryDraft: e.target.value })}
                            rows={4}
                            style={{ ...fieldInput, resize: "vertical", lineHeight: 1.6, fontFamily: "inherit" } as React.CSSProperties}
                          />
                        </div>

                        {/* Skills */}
                        <PillField
                          label="Skills"
                          pills={edit.skillsDraft}
                          inputValue={edit.newSkillInput}
                          pillColor="#0055B7"
                          borderColor="#93c5fd"
                          bgColor="#dbeafe"
                          onRemove={(s) => updateCard(card.project_name, { skillsDraft: edit.skillsDraft.filter((x) => x !== s) })}
                          onInputChange={(v) => updateCard(card.project_name, { newSkillInput: v })}
                          onAdd={(v) => {
                            if (v && !edit.skillsDraft.includes(v))
                              updateCard(card.project_name, { skillsDraft: [...edit.skillsDraft, v], newSkillInput: "" });
                            else
                              updateCard(card.project_name, { newSkillInput: "" });
                          }}
                          placeholder="Add a skill…"
                        />

                        {/* Frameworks */}
                        <PillField
                          label="Frameworks"
                          pills={edit.frameworksDraft}
                          inputValue={edit.newFrameworkInput}
                          pillColor="#6d28d9"
                          borderColor="#c4b5fd"
                          bgColor="#ede9fe"
                          onRemove={(f) => updateCard(card.project_name, { frameworksDraft: edit.frameworksDraft.filter((x) => x !== f) })}
                          onInputChange={(v) => updateCard(card.project_name, { newFrameworkInput: v })}
                          onAdd={(v) => {
                            if (v && !edit.frameworksDraft.includes(v))
                              updateCard(card.project_name, { frameworksDraft: [...edit.frameworksDraft, v], newFrameworkInput: "" });
                            else
                              updateCard(card.project_name, { newFrameworkInput: "" });
                          }}
                          placeholder="Add a framework…"
                        />

                        <div style={{ borderTop: "1px solid var(--border)" }} />

                        {/* Tone */}
                        <div>
                          <label style={sectionLabel}>Tone</label>
                          <input
                            value={edit.toneDraft}
                            onChange={(e) => updateCard(card.project_name, { toneDraft: e.target.value })}
                            placeholder="e.g. professional, casual, technical"
                            style={fieldInput}
                          />
                        </div>

                        {/* Themes */}
                        <PillField
                          label="Themes"
                          pills={edit.themesDraft}
                          inputValue={edit.newThemeInput}
                          pillColor="#0f766e"
                          borderColor="#5eead4"
                          bgColor="#ccfbf1"
                          onRemove={(t) => updateCard(card.project_name, { themesDraft: edit.themesDraft.filter((x) => x !== t) })}
                          onInputChange={(v) => updateCard(card.project_name, { newThemeInput: v })}
                          onAdd={(v) => {
                            if (v && !edit.themesDraft.includes(v))
                              updateCard(card.project_name, { themesDraft: [...edit.themesDraft, v], newThemeInput: "" });
                            else
                              updateCard(card.project_name, { newThemeInput: "" });
                          }}
                          placeholder="Add a theme…"
                        />

                        {/* Tags */}
                        <PillField
                          label="Tags"
                          pills={edit.tagsDraft}
                          inputValue={edit.newTagInput}
                          pillColor="#166534"
                          borderColor="#86efac"
                          bgColor="#dcfce7"
                          onRemove={(t) => updateCard(card.project_name, { tagsDraft: edit.tagsDraft.filter((x) => x !== t) })}
                          onInputChange={(v) => updateCard(card.project_name, { newTagInput: v })}
                          onAdd={(v) => {
                            if (v && !edit.tagsDraft.includes(v))
                              updateCard(card.project_name, { tagsDraft: [...edit.tagsDraft, v], newTagInput: "" });
                            else
                              updateCard(card.project_name, { newTagInput: "" });
                          }}
                          placeholder="Add a tag…"
                        />

                        {edit.error && (
                          <div style={{ color: "var(--danger-text)", fontSize: 13, padding: "8px 12px", background: "var(--danger-bg)", borderRadius: 8 }}>
                            {edit.error}
                          </div>
                        )}
                      </div>

                      {/* Modal footer */}
                      <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border)", flexShrink: 0, display: "flex", justifyContent: "flex-end" }}>
                        <button
                          onClick={() => updateCard(card.project_name, { showConfirmModal: true })}
                          disabled={edit.saving}
                          style={{
                            padding: "10px 20px",
                            borderRadius: 10,
                            border: "none",
                            background: edit.saving ? "var(--bg-surface-deep)" : "var(--btn-primary)",
                            color: edit.saving ? "var(--text-muted)" : "#fff",
                            cursor: edit.saving ? "not-allowed" : "pointer",
                            fontSize: 14,
                            fontWeight: 600,
                            opacity: edit.saving ? 0.6 : 1,
                          }}
                        >
                          {edit.saving ? "Saving…" : "Submit Changes"}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── Unsaved Changes Warning Modal ── */}
                {edit.showUnsavedWarning && (
                  <div
                    onClick={() => updateCard(card.project_name, { showUnsavedWarning: false })}
                    style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.72)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1300, padding: 24 }}
                  >
                    <div
                      onClick={(e) => e.stopPropagation()}
                      style={{ width: "100%", maxWidth: 420, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 24, boxShadow: "0 20px 60px rgba(0,0,0,0.45)" }}
                    >
                      <h2 style={{ marginTop: 0, fontSize: 18 }}>Unsaved Changes</h2>
                      <p style={{ color: "#444", lineHeight: 1.6, fontSize: 14 }}>
                        You have unsaved changes to{" "}
                        <strong>"{edit.titleDraft || card.project_name}"</strong>.
                        If you close now, your edits will be lost.
                      </p>
                      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 }}>
                        <button
                          onClick={() => updateCard(card.project_name, { showUnsavedWarning: false })}
                          style={{ padding: "9px 16px", borderRadius: 10, border: "1px solid var(--border)", background: "transparent", color: "#333", cursor: "pointer", fontSize: 13 }}
                        >
                          Keep Editing
                        </button>
                        <button
                          onClick={() => updateCard(card.project_name, { showUnsavedWarning: false, showEditModal: false })}
                          style={{ padding: "9px 18px", borderRadius: 10, border: "none", background: "#dc2626", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
                        >
                          Discard Changes
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── Confirm Save Modal ── */}
                {edit.showConfirmModal && (
                  <div
                    onClick={() => updateCard(card.project_name, { showConfirmModal: false })}
                    style={{
                      position: "fixed",
                      inset: 0,
                      background: "rgba(0,0,0,0.72)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      zIndex: 1200,
                      padding: 24,
                    }}
                  >
                    <div
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        width: "100%",
                        maxWidth: 420,
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 16,
                        padding: 24,
                        boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
                      }}
                    >
                      <h2 style={{ marginTop: 0, fontSize: 18 }}>Save Changes?</h2>
                      <p style={{ color: "#444", lineHeight: 1.6, fontSize: 14 }}>
                        You are about to save your edits to{" "}
                        <strong>"{edit.titleDraft || card.project_name}"</strong>.
                        These changes are permanent and will replace the current card content.
                      </p>
                      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 }}>
                        <button
                          onClick={() => updateCard(card.project_name, { showConfirmModal: false })}
                          style={{ padding: "9px 16px", borderRadius: 10, border: "1px solid var(--border)", background: "transparent", color: "#333", cursor: "pointer", fontSize: 13 }}
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveCard(card.project_name)}
                          style={{ padding: "9px 18px", borderRadius: 10, border: "none", background: "var(--btn-primary)", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
                        >
                          Save Changes
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ---- Refresh Confirmation Modal ---- */}
      {showRefreshConfirm && (
        <div
          onClick={() => { if (!refreshing) setShowRefreshConfirm(false); }}
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
              maxWidth: 420,
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: 16,
              padding: 24,
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Refresh Portfolio</h2>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Are you sure you want to refresh the Portfolio? Your changes may be lost.
            </p>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowRefreshConfirm(false)}
                disabled={refreshing}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: refreshing ? "var(--text-muted)" : "#444",
                  cursor: refreshing ? "not-allowed" : "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowRefreshConfirm(false); handleRefresh(); }}
                disabled={refreshing}
                style={{
                  padding: "10px 16px",
                  borderRadius: 10,
                  border: "none",
                  background: refreshing ? "var(--bg-surface-deep)" : "var(--btn-primary)",
                  color: refreshing ? "var(--text-muted)" : "#fff",
                  cursor: refreshing ? "not-allowed" : "pointer",
                  opacity: refreshing ? 0.7 : 1,
                  fontWeight: 600,
                }}
              >
                {refreshing ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---- Deploy Confirmation Modal ---- */}
      {showDeployConfirm && (
        <div
          onClick={() => {
            if (!deploying) setShowDeployConfirm(false);
          }}
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
              maxWidth: 420,
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: 16,
              padding: 24,
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Deploy to GitHub Pages</h2>
            <p style={{ color: "#444", lineHeight: 1.6 }}>
              Are you sure you want to deploy a static website of your portfolio
              to a GitHub Pages site? This will create or update the{" "}
              <strong>portfolio</strong> repository on your GitHub account and
              make it publicly accessible (note: it may take a few minutes for
              the site to update).
            </p>

            <p style={{ color: "#444", lineHeight: 1.6 }}>
              <strong>
                WARNING: This action will wipe and replace any existing files in
                the repository.
              </strong>
            </p>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowDeployConfirm(false)}
                disabled={deploying}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: deploying ? "#777" : "#444",
                  cursor: deploying ? "not-allowed" : "pointer",
                }}
              >
                Cancel
              </button>

              <button
                onClick={handleExport}
                disabled={deploying}
                style={{
                  padding: "10px 16px",
                  borderRadius: 10,
                  border: "none",
                  background: deploying ? "var(--bg-surface-deep)" : "#002145",
                  color: "#fff",
                  cursor: deploying ? "not-allowed" : "pointer",
                  opacity: deploying ? 0.7 : 1,
                }}
              >
                {deploying ? "Deploying..." : "Deploy"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---- Delete Confirmation Modal ---- */}
      {showDeleteConfirm && (
        <div
          onClick={() => {
            if (!deleting) setShowDeleteConfirm(false);
          }}
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
            <h2 style={{ marginTop: 0 }}>Delete Portfolio</h2>
            <p style={{ color: "#444", lineHeight: 1.6 }}>
              Are you sure you want to delete{" "}
              <strong>"{portfolio.title}"</strong>? This will permanently remove
              the portfolio and all its content. This cannot be undone.
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

            <div
              style={{
                display: "flex",
                gap: 10,
                justifyContent: "flex-end",
              }}
            >
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: deleting ? "#777" : "#444",
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
                {deleting ? "Deleting..." : "Delete Portfolio"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
