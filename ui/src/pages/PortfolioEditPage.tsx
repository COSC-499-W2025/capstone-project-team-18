import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/apiClient";
import TextBlockEditor from "../components/blocks/TextBlockEditor";
import TextListBlockEditor from "../components/blocks/TextListBlockEditor";
import ContributionMap from "../components/ContributionMap";
import SkillTimelineGraph from "../components/SkillTimelineGraph";

// ---- Types ----------------------------------------------------------------

type BlockMetadata = {
  in_conflict: boolean;
  last_generated_at?: string;
  last_user_edit_at?: string;
  conflict_content?: any;
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
  is_showcase: boolean;
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

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function pillStyle(color?: string) {
  return {
    fontSize: 11,
    color: color ?? "#ddd",
    border: `1px solid ${color ? color + "44" : "#2a2a2a"}`,
    borderRadius: 999,
    padding: "3px 8px",
    whiteSpace: "nowrap" as const,
    background: color ? color + "11" : "transparent",
  };
}

// ---- Component ------------------------------------------------------------

export default function PortfolioEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Title editing
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Action states
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Per-card edit state: { [project_name]: { titleDraft, summaryDraft, tagsDraft, saving, error } }
  const [cardEdits, setCardEdits] = useState<
    Record<
      string,
      {
        titleDraft: string;
        summaryDraft: string;
        tagsDraft: string;
        saving: boolean;
        error: string | null;
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
  const [contributionLoading, setContributionLoading] = useState(false);

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
      const data = (await api.getPortfolio(id!)) as Portfolio;
      setPortfolio(data);
      setTitleDraft(data.title);
      initCardEdits(data.project_cards);
      initBlockEdits(data.sections);

      try {
        setContributionLoading(true);
        const projectNames = data.project_cards.map((c) => c.project_name);
        const personal_timeline: Record<string, number> = {};
        const total_timeline: Record<string, number> = {};
        const skill_timeline: Record<string, Record<string, number>> = {};

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
      } catch (e: any) {
        // Silently fail contribution loading so it doesn't block the page
        console.warn("Failed to load contribution map:", e?.message);
        setContributionData(null);
        setSkillTimelineData({});
      } finally {
        setContributionLoading(false);
      }
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
        titleDraft: c.title_override ?? "",
        summaryDraft: c.summary_override ?? "",
        tagsDraft: (c.tags_override ?? c.tags ?? []).join(", "),
        saving: false,
        error: null,
      };
    }
    setCardEdits(edits);
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
    setExporting(true);
    let objectUrl: string | null = null;
    try {
      const blob = await api.exportPortfolio(id!);
      objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = `portfolio_${id}.zip`;
      a.click();
    } catch (e: any) {
      setError(e?.message ?? "Failed to export.");
    } finally {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setExporting(false);
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

  async function handleSaveCard(projectName: string) {
    const edits = cardEdits[projectName];
    if (!edits) return;
    setCardEdits((prev) => ({
      ...prev,
      [projectName]: { ...prev[projectName], saving: true, error: null },
    }));
    try {
      const tagsArr = edits.tagsDraft
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await api.patchPortfolioCard(id!, projectName, {
        title_override: edits.titleDraft || null,
        summary_override: edits.summaryDraft || null,
        tags_override: tagsArr.length > 0 ? tagsArr : null,
      });
      setCardEdits((prev) => ({
        ...prev,
        [projectName]: { ...prev[projectName], saving: false, error: null },
      }));
    } catch (e: any) {
      setCardEdits((prev) => ({
        ...prev,
        [projectName]: {
          ...prev[projectName],
          saving: false,
          error: e?.message ?? "Failed to save card.",
        },
      }));
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
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
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
          to="/portfolios"
          style={{ color: "#6f7cff", fontSize: 14, textDecoration: "none" }}
        >
          ← Back to Portfolios
        </Link>
        <div
          style={{
            marginTop: 16,
            border: "1px solid #3a1f1f",
            borderRadius: 16,
            padding: 20,
            background: "#1a1111",
            color: "#ff8a8a",
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
  const sortedCards = [...portfolio.project_cards].sort(
    (a, b) => (a.is_showcase === b.is_showcase ? 0 : a.is_showcase ? -1 : 1)
  );

  // ---- Render: Main -------------------------------------------------------

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      {/* Back */}
      <Link
        to="/portfolios"
        style={{ color: "#6f7cff", fontSize: 14, textDecoration: "none" }}
      >
        ← Back to Portfolios
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
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  padding: "6px 10px",
                  borderRadius: 10,
                  border: "1px solid #2a2a2a",
                  background: "#111",
                  color: "#fff",
                  minWidth: 280,
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
                }}
              >
                Apply
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ margin: 0, fontSize: 28 }}>{titleDraft}</h1>
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

          <div
            style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 10 }}
          >
            <span style={{ fontSize: 13, color: "#666" }}>
              Updated: {formatDate(portfolio.metadata.last_updated_at)}
            </span>
          </div>
        </div>

        {/* Action bar */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{ padding: "10px 14px", opacity: saving ? 0.6 : 1 }}
          >
            {saving ? "Saving..." : "Save"}
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid #2a2a2a",
              borderRadius: 10,
              color: refreshing ? "#666" : "#ddd",
              cursor: refreshing ? "not-allowed" : "pointer",
              opacity: refreshing ? 0.6 : 1,
            }}
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>

          <button
            onClick={handleExport}
            disabled={exporting}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "1px solid #2a2a2a",
              borderRadius: 10,
              color: exporting ? "#666" : "#ddd",
              cursor: exporting ? "not-allowed" : "pointer",
              opacity: exporting ? 0.6 : 1,
            }}
          >
            {exporting ? "Exporting..." : "Export ZIP"}
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
            }}
          >
            Delete
          </button>
        </div>
      </div>

      {/* Save error */}
      {saveError && (
        <div style={{ color: "#ff8a8a", fontSize: 14, marginTop: 10 }}>
          {saveError}
        </div>
      )}

      {/* General error (post-load) */}
      {error && (
        <div
          style={{
            marginTop: 16,
            color: "#ff8a8a",
            fontSize: 14,
            border: "1px solid #3a1f1f",
            borderRadius: 12,
            padding: 12,
            background: "#1a1111",
          }}
        >
          {error}
        </div>
      )}

      {contributionLoading && (
        <div style={{ marginTop: 16, color: "#999", fontSize: 13 }}>
          Loading activity graphs...
        </div>
      )}

      {/* ---- Contribution Map ---- */}
      {contributionData && (
        <div style={{ marginTop: 40 }}>
          <ContributionMap
            personalTimeline={contributionData.personal_timeline}
            totalTimeline={contributionData.total_timeline}
          />
        </div>
      )}

      {/* ---- Skill Timeline ---- */}
      {Object.keys(skillTimelineData).length > 0 && (
        <div style={{ marginTop: 24 }}>
          <SkillTimelineGraph data={skillTimelineData} />
        </div>
      )}


      {/* ---- Project Cards ---- */}
      <div style={{ marginTop: 40 }}>
        <h2 style={{ marginBottom: 16 }}>Project Cards</h2>

        {sortedCards.length === 0 && (
          <div
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
              color: "#999",
            }}
          >
            No project cards.
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: 16,
          }}
        >
          {sortedCards.map((card) => {
            const edit = cardEdits[card.project_name];
            if (!edit) return null;
            return (
              <div
                key={card.project_name}
                style={{
                  border: card.is_showcase
                    ? "1px solid #b8860b"
                    : "1px solid #2a2a2a",
                  borderRadius: 16,
                  padding: 18,
                  background: "#161616",
                }}
              >
                {/* Card header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: 14,
                    gap: 10,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 16 }}>
                    {card.project_name}
                  </div>
                  <button
                    onClick={() => handleToggleShowcase(card.project_name)}
                    style={{
                      padding: "4px 10px",
                      borderRadius: 999,
                      border: `1px solid ${card.is_showcase ? "#b8860b" : "#2a2a2a"}`,
                      background: "transparent",
                      color: card.is_showcase ? "#f5c518" : "#999",
                      cursor: "pointer",
                      fontSize: 12,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {card.is_showcase ? "★ Showcase" : "☆ Showcase"}
                  </button>
                </div>

                {/* Read-only metadata pills */}
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 6,
                    marginBottom: 14,
                  }}
                >
                  {card.themes?.map((t) => (
                    <span key={t} style={pillStyle("#6f7cff")}>
                      {t}
                    </span>
                  ))}
                  {card.tones && (
                    <span style={pillStyle("#8ad6a2")}>{card.tones}</span>
                  )}
                  {card.skills?.slice(0, 4).map((s) => (
                    <span key={s} style={pillStyle()}>
                      {s}
                    </span>
                  ))}
                </div>

                {/* Editable fields */}
                <div style={{ display: "grid", gap: 10 }}>
                  <div>
                    <label
                      style={{
                        fontSize: 12,
                        color: "#aaa",
                        display: "block",
                        marginBottom: 4,
                      }}
                    >
                      Title Override
                    </label>
                    <input
                      value={edit.titleDraft}
                      onChange={(e) =>
                        setCardEdits((prev) => ({
                          ...prev,
                          [card.project_name]: {
                            ...prev[card.project_name],
                            titleDraft: e.target.value,
                          },
                        }))
                      }
                      placeholder="Leave blank to use project name"
                      style={{
                        width: "100%",
                        padding: "8px 10px",
                        borderRadius: 8,
                        border: "1px solid #2a2a2a",
                        background: "#111",
                        color: "#fff",
                        fontSize: 13,
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

                  <div>
                    <label
                      style={{
                        fontSize: 12,
                        color: "#aaa",
                        display: "block",
                        marginBottom: 4,
                      }}
                    >
                      Summary Override
                    </label>
                    <textarea
                      value={edit.summaryDraft}
                      onChange={(e) =>
                        setCardEdits((prev) => ({
                          ...prev,
                          [card.project_name]: {
                            ...prev[card.project_name],
                            summaryDraft: e.target.value,
                          },
                        }))
                      }
                      placeholder="Leave blank to use generated summary"
                      rows={3}
                      style={{
                        width: "100%",
                        padding: "8px 10px",
                        borderRadius: 8,
                        border: "1px solid #2a2a2a",
                        background: "#111",
                        color: "#fff",
                        fontSize: 13,
                        resize: "vertical",
                        boxSizing: "border-box",
                        fontFamily: "inherit",
                      }}
                    />
                  </div>

                  <div>
                    <label
                      style={{
                        fontSize: 12,
                        color: "#aaa",
                        display: "block",
                        marginBottom: 4,
                      }}
                    >
                      Tags Override (comma-separated)
                    </label>
                    <input
                      value={edit.tagsDraft}
                      onChange={(e) =>
                        setCardEdits((prev) => ({
                          ...prev,
                          [card.project_name]: {
                            ...prev[card.project_name],
                            tagsDraft: e.target.value,
                          },
                        }))
                      }
                      placeholder="e.g. python, api, machine-learning"
                      style={{
                        width: "100%",
                        padding: "8px 10px",
                        borderRadius: 8,
                        border: "1px solid #2a2a2a",
                        background: "#111",
                        color: "#fff",
                        fontSize: 13,
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                </div>

                {edit.error && (
                  <div
                    style={{ color: "#ff8a8a", fontSize: 12, marginTop: 8 }}
                  >
                    {edit.error}
                  </div>
                )}

                <button
                  onClick={() => handleSaveCard(card.project_name)}
                  disabled={edit.saving}
                  style={{
                    marginTop: 12,
                    padding: "8px 14px",
                    borderRadius: 10,
                    border: "none",
                    background: edit.saving ? "#202020" : "#2b2b2b",
                    color: "#fff",
                    cursor: edit.saving ? "not-allowed" : "pointer",
                    opacity: edit.saving ? 0.6 : 1,
                    fontSize: 13,
                  }}
                >
                  {edit.saving ? "Saving..." : "Save Card"}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* ---- Narrative Sections ---- */}
      {sortedSections.length > 0 && (
        <div style={{ marginTop: 40 }}>
          <h2 style={{ marginBottom: 16 }}>Narrative Sections</h2>

          <div style={{ display: "grid", gap: 24 }}>
            {sortedSections.map((section) => (
              <div
                key={section.id}
                style={{
                  border: "1px solid #2a2a2a",
                  borderRadius: 16,
                  padding: 20,
                  background: "#161616",
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
                      <div
                        key={blockTag}
                        style={{
                          border: block.metadata?.in_conflict
                            ? "1px solid #ff8a8a"
                            : "1px solid #2a2a2a",
                          borderRadius: 12,
                          padding: 14,
                          background: "#111",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: 10,
                          }}
                        >
                          <span
                            style={{
                              fontSize: 12,
                              color: "#999",
                              fontFamily: "monospace",
                            }}
                          >
                            {blockTag}
                          </span>
                          <span
                            style={{
                              fontSize: 11,
                              color: "#666",
                              border: "1px solid #2a2a2a",
                              borderRadius: 999,
                              padding: "2px 8px",
                            }}
                          >
                            {block.content_type}
                          </span>
                        </div>

                        {block.metadata?.in_conflict && (
                          <div
                            style={{
                              color: "#ff8a8a",
                              fontSize: 12,
                              marginBottom: 10,
                              padding: "6px 10px",
                              background: "#3a1111",
                              borderRadius: 8,
                            }}
                          >
                            Conflict detected — system has new content
                          </div>
                        )}

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
                              border: "1px solid #2a2a2a",
                              background: "#0d0d0d",
                              color: "#999",
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
              background: "#1b1b1b",
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 24,
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Delete Portfolio</h2>
            <p style={{ color: "#ccc", lineHeight: 1.6 }}>
              Are you sure you want to delete{" "}
              <strong>"{portfolio.title}"</strong>? This will permanently remove
              the portfolio and all its content. This cannot be undone.
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
                {deleting ? "Deleting..." : "Delete Portfolio"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
