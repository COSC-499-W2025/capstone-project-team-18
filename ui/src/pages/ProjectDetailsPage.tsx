import { type ReactNode, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/apiClient";

type WeightedSkill = { name?: string; skill?: string; weight?: number } | string;

type ProjectReport = {
  project_name: string;
  user_config_used?: number | null;
  image_data?: string | null;
  created_at?: string;
  last_updated?: string;
  statistic?: Record<string, unknown>;
  [key: string]: unknown;
};

function isNotFoundError(msg: string) {
  return msg.includes("API request failed (404)");
}

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function getImageSrc(base64: string): string {
  if (base64.startsWith("/9j/")) return `data:image/jpeg;base64,${base64}`;
  if (base64.startsWith("iVBOR")) return `data:image/png;base64,${base64}`;
  if (base64.startsWith("R0lG")) return `data:image/gif;base64,${base64}`;
  if (base64.startsWith("UklG")) return `data:image/webp;base64,${base64}`;
  return `data:image/jpeg;base64,${base64}`;
}

/** Unwrap stat value — handles both raw value and {value: ...} wrapper */
function getStat(statistic: Record<string, unknown>, key: string): unknown {
  const raw = statistic[key];
  if (raw === null || raw === undefined) return undefined;
  if (
    typeof raw === "object" &&
    !Array.isArray(raw) &&
    "value" in (raw as Record<string, unknown>)
  ) {
    return (raw as Record<string, unknown>).value;
  }
  return raw;
}

function getSkillName(s: WeightedSkill): string {
  if (typeof s === "string") return s;
  const obj = s as Record<string, unknown>;
  // Handle {"__type__": "dataclass", "value": {"skill_name": "..."}} wrapper
  if (obj.__type__ === "dataclass" && obj.value && typeof obj.value === "object") {
    const val = obj.value as Record<string, unknown>;
    return (val.skill_name as string) ?? (val.name as string) ?? "";
  }
  return (obj.name as string) ?? (obj.skill as string) ?? (obj.skill_name as string) ?? "";
}

/** Strip enum serialization prefix: "__enum__:CodingLanguage:TypeScript" → "TypeScript" */
function parseLanguageName(key: string): string {
  if (key.startsWith("__enum__:")) {
    const parts = key.split(":");
    return parts[parts.length - 1];
  }
  return key;
}

function parseLanguageRatio(value: unknown): Array<{ lang: string; ratio: number }> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  return Object.entries(value as Record<string, unknown>)
    .map(([key, r]) => ({ lang: parseLanguageName(key), ratio: Number(r) }))
    .filter(({ ratio }) => ratio > 0 && !Number.isNaN(ratio))
    .sort((a, b) => b.ratio - a.ratio);
}

function parseWeightedSkills(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((s) => getSkillName(s as WeightedSkill)).filter(Boolean);
}

function parseStringList(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter((s): s is string => typeof s === "string");
  if (typeof value === "string") return [value];
  return [];
}

function parseCommitDistribution(value: unknown): Array<{ type: string; pct: number }> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  // Backend stores values as 0-100 percentages already (not 0-1 ratios)
  return Object.entries(value as Record<string, unknown>)
    .map(([type, v]) => ({ type, pct: Math.round(Number(v)) }))
    .filter(({ pct }) => pct > 0)
    .sort((a, b) => b.pct - a.pct);
}

// GitHub Linguist-style colors per language
const LANG_COLOR_MAP: Record<string, string> = {
  Python:     "#3572A5",
  JavaScript: "#f1e05a",
  TypeScript: "#3178c6",
  Java:       "#b07219",
  "C++":      "#f34b7d",
  C:          "#555555",
  "C#":       "#178600",
  PHP:        "#4F5D95",
  Ruby:       "#701516",
  Swift:      "#F05138",
  Go:         "#00ADD8",
  Rust:       "#DEA584",
  HTML:       "#e34c26",
  CSS:        "#563d7c",
  SQL:        "#e38c00",
  Shell:      "#89e051",
  R:          "#198CE7",
};
const LANG_FALLBACK_COLORS = [
  "#6f7cff", "#ff7c6f", "#7cff9a", "#ffd06f",
  "#c06fff", "#6fecff", "#ff6fb8", "#a8ff6f",
];

const COMMIT_COLORS: Record<string, string> = {
  feature: "#6f7cff",
  feat: "#6f7cff",
  fix: "#ff7c6f",
  bugfix: "#ff7c6f",
  refactor: "#ffd06f",
  docs: "#7cff9a",
  documentation: "#7cff9a",
  test: "#c06fff",
  tests: "#c06fff",
  chore: "#6fecff",
  style: "#ff6fb8",
  perf: "#a8ff6f",
  performance: "#a8ff6f",
};

// --- UI sub-components ---

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "14px 18px",
        background: "var(--bg-surface)",
      }}
    >
      <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "#666", marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

function SectionCard({
  title,
  children,
  mb = 20,
  centerContent = false,
}: {
  title: string;
  children: ReactNode;
  mb?: number;
  centerContent?: boolean;
}) {
  return (
    <section
      style={{
        border: "1px solid var(--border)",
        borderRadius: 16,
        padding: 20,
        background: "var(--bg-surface)",
        marginBottom: mb,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, color: "#444", fontWeight: 600 }}>
        {title}
      </h3>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: centerContent ? "center" : "flex-start" }}>
        {children}
      </div>
    </section>
  );
}

/** Expand 3-char hex to 6-char so alpha suffixes produce valid 8-char hex */
function expandHex(hex: string): string {
  const h = hex.startsWith("#") ? hex.slice(1) : hex;
  const expanded = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  return `#${expanded}`;
}

function TagChips({ items, color = "#6f7cff" }: { items: string[]; color?: string }) {
  if (!items.length) return <span style={{ color: "#555", fontSize: 13 }}>—</span>;
  const base = expandHex(color);
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {items.map((tag) => (
        <span
          key={tag}
          style={{
            padding: "3px 10px",
            borderRadius: 999,
            background: `${base}1a`,
            border: `1px solid ${base}44`,
            color,
            fontSize: 12,
            lineHeight: 1.6,
          }}
        >
          {tag}
        </span>
      ))}
    </div>
  );
}

function LabelRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "140px 1fr",
        gap: 12,
        alignItems: "start",
        paddingBottom: 14,
        borderBottom: "1px solid var(--border)",
        marginBottom: 14,
      }}
    >
      <span style={{ fontSize: 12, color: "#777", paddingTop: 4 }}>{label}</span>
      <div>{children}</div>
    </div>
  );
}

function ProgressBar({
  label,
  value,
  color = "#6f7cff",
}: {
  label: string;
  value: number;
  color?: string;
}) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 100)));
  return (
    <div style={{ marginBottom: 14 }}>
      <div
        style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 6 }}
      >
        <span style={{ color: "#999" }}>{label}</span>
        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{pct}%</span>
      </div>
      <div style={{ height: 8, background: "var(--bg-surface-deep)", borderRadius: 4, overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: color,
            borderRadius: 4,
            transition: "width 0.5s ease",
          }}
        />
      </div>
    </div>
  );
}

function LanguageDonut({ langs }: { langs: Array<{ lang: string; ratio: number }> }) {
  const total = langs.reduce((s, d) => s + d.ratio, 0);
  if (total === 0) return null;

  const segments = langs.map((d, i) => ({
    ...d,
    color: LANG_COLOR_MAP[d.lang] ?? LANG_FALLBACK_COLORS[i % LANG_FALLBACK_COLORS.length],
    pct: (d.ratio / total) * 100,
  }));

  let cum = 0;
  const stops = segments.map((s) => {
    const start = cum;
    cum += s.pct;
    return `${s.color} ${start.toFixed(2)}% ${cum.toFixed(2)}%`;
  });

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 28, flexWrap: "wrap" }}>
      <div style={{ position: "relative", width: 140, height: 140, flexShrink: 0 }}>
        <div
          style={{
            width: 140,
            height: 140,
            borderRadius: "50%",
            background: `conic-gradient(${stops.join(", ")})`,
          }}
        />
        {/* Inner circle cutout for donut effect */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 72,
            height: 72,
            borderRadius: "50%",
            background: "var(--bg-surface)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ fontSize: 10, color: "#666", textAlign: "center", lineHeight: 1.3 }}>
            {langs.length} lang{langs.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {segments.map((s) => (
          <div key={s.lang} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: 2,
                background: s.color,
                flexShrink: 0,
              }}
            />
            <span style={{ color: "#444", minWidth: 80 }}>{s.lang}</span>
            <span style={{ color: "#777" }}>{s.pct.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CommitTypeChart({ items }: { items: Array<{ type: string; pct: number }> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {items.map(({ type, pct }) => {
        const color = COMMIT_COLORS[type.toLowerCase()] ?? "#888";
        return (
          <div key={type}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 13,
                marginBottom: 5,
              }}
            >
              <span style={{ color: "#555", textTransform: "capitalize" }}>{type}</span>
              <span style={{ color: "#777" }}>{pct}%</span>
            </div>
            <div style={{ height: 6, background: "var(--bg-surface-deep)", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 3 }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function WorkPatternBadge({ pattern }: { pattern: string }) {
  const cfg: Record<string, { color: string; label: string }> = {
    consistent: { color: "#7cff9a", label: "Consistent" },
    sprint: { color: "#ffd06f", label: "Sprint-based" },
    burst: { color: "#ff7c6f", label: "Burst" },
    sporadic: { color: "#c06fff", label: "Sporadic" },
  };
  const c = cfg[pattern.toLowerCase()] ?? { color: "#888", label: pattern };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 12px",
        borderRadius: 999,
        background: `${c.color}1a`,
        border: `1px solid ${c.color}44`,
        color: c.color,
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      {c.label}
    </span>
  );
}

// --- Main Page ---

export default function ProjectDetailsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const backTo: string = (location.state as { from?: string })?.from ?? "/projects";
  const backLabel = backTo === "/" ? "← Back to Dashboard" : "← Back to Projects";
  const { id } = useParams();
  const projectName = id ?? "";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectReport | null>(null);
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
    } catch (e: unknown) {
      setImageUploadError((e as { message?: string })?.message ?? "Failed to upload image");
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
    } catch (e: unknown) {
      setImageUploadError((e as { message?: string })?.message ?? "Failed to remove image");
    } finally {
      setImageRemoving(false);
    }
  }

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

        const projectRes = (await api.getProject(projectName)) as ProjectReport;
        if (!alive) return;

        setProject(projectRes);
        setLoading(false);
      } catch (e: unknown) {
        if (!alive) return;
        setError((e as { message?: string })?.message ?? "Failed to load project");
        setLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [projectName, navigate]);

  // --- Parse statistics ---
  const stat = project?.statistic ?? {};

  const startDate = getStat(stat, "PROJECT_START_DATE") as string | undefined;
  const endDate = getStat(stat, "PROJECT_END_DATE") as string | undefined;
  const totalLines = getStat(stat, "TOTAL_PROJECT_LINES") as number | undefined;
  const totalAuthors = getStat(stat, "TOTAL_AUTHORS") as number | undefined;
  const isGroupProject = getStat(stat, "IS_GROUP_PROJECT") as boolean | undefined;
  const workPattern = getStat(stat, "WORK_PATTERN") as string | undefined;
  const projectTone = getStat(stat, "PROJECT_TONE") as string | undefined;
  const collaborationRole = getStat(stat, "COLLABORATION_ROLE") as string | undefined;
  const roleDescription = getStat(stat, "ROLE_DESCRIPTION") as string | undefined;
  const userCommitPct = getStat(stat, "USER_COMMIT_PERCENTAGE") as number | undefined;
  const totalContribPct = getStat(stat, "TOTAL_CONTRIBUTION_PERCENTAGE") as number | undefined;
  const activityMetrics = getStat(stat, "ACTIVITY_METRICS") as
    | Record<string, unknown>
    | undefined;

  const languageRatio = parseLanguageRatio(getStat(stat, "CODING_LANGUAGE_RATIO"));
  const skills = parseWeightedSkills(getStat(stat, "PROJECT_SKILLS_DEMONSTRATED"));
  const frameworks = parseWeightedSkills(getStat(stat, "PROJECT_FRAMEWORKS"));
  const projectTags = parseStringList(getStat(stat, "PROJECT_TAGS"));
  const projectThemes = parseStringList(getStat(stat, "PROJECT_THEMES"));
  const commitDistribution = parseCommitDistribution(
    getStat(stat, "COMMIT_TYPE_DISTRIBUTION")
  );

  const hasAnyStats = Object.keys(stat).length > 0;

  const durationLabel = (() => {
    if (!startDate && !endDate) return null;
    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
      const days = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
      if (days < 1) return "< 1 day";
      if (days < 30) return `${days} day${days !== 1 ? "s" : ""}`;
      if (days < 365) return `${Math.round(days / 30)} month${Math.round(days / 30) !== 1 ? "s" : ""}`;
      return `${(days / 365).toFixed(1)} yrs`;
    }
    return startDate ? formatDate(startDate) : formatDate(endDate);
  })();

  const durationSub =
    startDate && endDate
      ? `${formatDate(startDate)} – ${formatDate(endDate)}`
      : undefined;

  const avgCommitsPerWeek =
    activityMetrics &&
    typeof activityMetrics.avg_commits_per_week === "number"
      ? activityMetrics.avg_commits_per_week
      : undefined;

  const consistencyScore =
    activityMetrics &&
    typeof activityMetrics.consistency_score === "number"
      ? activityMetrics.consistency_score
      : undefined;

  // Decide which quick-stat cards to show
  const quickStats: Array<{ label: string; value: string; sub?: string }> = [];
  if (durationLabel) quickStats.push({ label: "Duration", value: durationLabel, sub: durationSub });
  if (totalLines !== undefined)
    quickStats.push({ label: "Lines of Code", value: totalLines.toLocaleString() });
  if (totalAuthors !== undefined)
    quickStats.push({
      label: "Contributors",
      value: totalAuthors === 1 || isGroupProject === false ? "Solo Project" : String(totalAuthors),
      sub: totalAuthors === 1 || isGroupProject === false ? undefined : "Group project",
    });
  if (avgCommitsPerWeek !== undefined)
    quickStats.push({
      label: "Avg Commits / Week",
      value: avgCommitsPerWeek.toFixed(1),
    });
  if (workPattern)
    quickStats.push({
      label: "Work Pattern",
      value: workPattern.charAt(0).toUpperCase() + workPattern.slice(1).toLowerCase(),
    });

  // Only show contribution section for group projects (solo = always 100%, not useful)
  const showContributions =
    isGroupProject === true &&
    (userCommitPct !== undefined || totalContribPct !== undefined);
  const showActivity = commitDistribution.length > 0 || consistencyScore !== undefined;
  const showCharacter = projectTone || projectTags.length > 0 || projectThemes.length > 0;
  const showRole = collaborationRole || roleDescription;

  // --- Render ---
  return (
    <div style={{ padding: "40px 48px" }}>
      {/* Back button */}
      <div style={{ marginBottom: 20 }}>
        <button
          type="button"
          onClick={() => navigate(backTo)}
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            color: "var(--accent)",
            cursor: "pointer",
            fontSize: 16,
          }}
        >
          {backLabel}
        </button>
      </div>

      {loading && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 16,
            padding: 20,
            background: "var(--bg-surface)",
          }}
        >
          Loading project details...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            border: "1px solid var(--danger-bg-strong)",
            borderRadius: 16,
            padding: 20,
            background: "var(--danger-bg)",
            color: "var(--danger-text)",
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
          {/* ── Hero: title + metadata + quick stats + thumbnail ── */}
          <div
            style={{
              display: "flex",
              gap: 24,
              marginBottom: 24,
              alignItems: "stretch",
              flexWrap: "wrap",
            }}
          >
            {/* Title + metadata + quick stats */}
            <div style={{ flex: 1, minWidth: 200 }}>
              <h1 style={{ margin: 0, marginBottom: 8, fontSize: 32, fontWeight: 700, letterSpacing: "-0.5px" }}>{project.project_name}</h1>
              <div style={{ fontSize: 13, color: "#666", marginBottom: 20 }}>
                Added {formatDate(project.created_at)}
                {project.last_updated && ` · Updated ${formatDate(project.last_updated)}`}
              </div>

              {quickStats.length > 0 && (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                    gap: 10,
                  }}
                >
                  {quickStats.map((s) => (
                    <StatCard key={s.label} label={s.label} value={s.value} sub={s.sub} />
                  ))}
                </div>
              )}
            </div>

            {/* Thumbnail column — right side, stretches to match title column height */}
            <div style={{ flexShrink: 0, display: "flex", flexDirection: "column" }}>
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
                <div
                  style={{
                    width: 260,
                    flex: 1,
                    overflow: "hidden",
                    borderRadius: 14,
                    border: "1px solid var(--border)",
                    background: "#f0f0f0",
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
              ) : (
                <button
                  type="button"
                  disabled={imageUploading}
                  onClick={() => imageInputRef.current?.click()}
                  style={{
                    width: 260,
                    flex: 1,
                    border: "1px dashed #3a3a3a",
                    borderRadius: 14,
                    background: "var(--bg-input)",
                    cursor: imageUploading ? "not-allowed" : "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    opacity: imageUploading ? 0.6 : 1,
                  }}
                >
                  <span style={{ fontSize: 28, color: "#444" }}>+</span>
                  <span style={{ fontSize: 12, color: "#555" }}>
                    {imageUploading ? "Uploading…" : "Add Thumbnail"}
                  </span>
                </button>
              )}

              {project.image_data && (
                <div style={{ display: "flex", gap: 6, marginTop: 8, justifyContent: "center" }}>
                  <button
                    type="button"
                    disabled={imageUploading || imageRemoving}
                    onClick={() => imageInputRef.current?.click()}
                    style={{
                      border: "1px solid var(--border)",
                      borderRadius: 7,
                      background: "transparent",
                      color: "var(--accent)",
                      padding: "5px 10px",
                      cursor: imageUploading || imageRemoving ? "not-allowed" : "pointer",
                      fontSize: 12,
                      opacity: imageUploading || imageRemoving ? 0.6 : 1,
                    }}
                  >
                    {imageUploading ? "Uploading…" : "Change"}
                  </button>
                  <button
                    type="button"
                    disabled={imageUploading || imageRemoving}
                    onClick={handleImageRemove}
                    style={{
                      border: "1px solid #4a2020",
                      borderRadius: 7,
                      background: "transparent",
                      color: "var(--danger-text)",
                      padding: "5px 10px",
                      cursor: imageUploading || imageRemoving ? "not-allowed" : "pointer",
                      fontSize: 12,
                      opacity: imageUploading || imageRemoving ? 0.6 : 1,
                    }}
                  >
                    {imageRemoving ? "Removing…" : "Remove"}
                  </button>
                </div>
              )}

              {imageUploadError && (
                <div style={{ color: "var(--danger-text)", fontSize: 11, marginTop: 6, maxWidth: 200, textAlign: "center" }}>
                  {imageUploadError}
                </div>
              )}
            </div>
          </div>

          {/* ── Row: Language Breakdown + Activity Breakdown ── */}
          {(languageRatio.length > 0 || showActivity) && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                gap: 16,
                marginBottom: 20,
              }}
            >
              {languageRatio.length > 0 && (
                <SectionCard title="Language Breakdown" mb={0} centerContent>
                  <LanguageDonut langs={languageRatio} />
                </SectionCard>
              )}

              {showActivity && (
                <SectionCard title="Activity Breakdown" mb={0}>
                  {consistencyScore !== undefined && (
                    <div style={{ marginBottom: commitDistribution.length > 0 ? 20 : 0 }}>
                      <ProgressBar
                        label="Consistency score"
                        value={consistencyScore}
                        color="#ffd06f"
                      />
                    </div>
                  )}
                  {commitDistribution.length > 0 && (
                    <>
                      <div style={{ fontSize: 12, color: "#777", marginBottom: 10 }}>
                        Commit type distribution
                      </div>
                      <CommitTypeChart items={commitDistribution} />
                    </>
                  )}
                </SectionCard>
              )}
            </div>
          )}

          {/* ── Row: Your Contribution + Collaboration Role (group projects only) ── */}
          {(showContributions || showRole) && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: 16,
                marginBottom: 20,
              }}
            >
              {showContributions && (
                <SectionCard title="Your Contribution" mb={0}>
                  {userCommitPct !== undefined && (
                    <ProgressBar label="Commit share" value={userCommitPct / 100} color="#6f7cff" />
                  )}
                  {totalContribPct !== undefined && (
                    <ProgressBar
                      label="Lines of code share"
                      value={totalContribPct / 100}
                      color="#7cff9a"
                    />
                  )}
                </SectionCard>
              )}

              {showRole && (
                <SectionCard title="Collaboration Role" mb={0}>
                  {collaborationRole && (
                    <div style={{ marginBottom: roleDescription ? 12 : 0 }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "3px 12px",
                          borderRadius: 999,
                          background: "#6f7cff1a",
                          border: "1px solid #6f7cff44",
                          color: "var(--accent)",
                          fontSize: 13,
                          fontWeight: 600,
                          textTransform: "capitalize",
                        }}
                      >
                        {collaborationRole}
                      </span>
                    </div>
                  )}
                  {roleDescription && (
                    <p style={{ margin: 0, color: "#555", fontSize: 14, lineHeight: 1.7 }}>
                      {roleDescription}
                    </p>
                  )}
                </SectionCard>
              )}
            </div>
          )}

          {/* ── Skills & Technologies (full width) ── */}
          {(skills.length > 0 || frameworks.length > 0) && (
            <SectionCard title="Skills & Technologies">
              {skills.length > 0 && (
                <LabelRow label="Skills">
                  <TagChips items={skills} color="#ddd" />
                </LabelRow>
              )}
              {frameworks.length > 0 && (
                <LabelRow label="Frameworks & Libraries">
                  <TagChips items={frameworks} color="#e08060" />
                </LabelRow>
              )}
            </SectionCard>
          )}

          {/* ── Project Character: tone, themes, tags (full width) ── */}
          {showCharacter && (
            <SectionCard title="Project Character">
              {projectTone && (
                <LabelRow label="Tone">
                  <span
                    style={{
                      display: "inline-block",
                      padding: "3px 12px",
                      borderRadius: 999,
                      background: "#ffd06f1a",
                      border: "1px solid #ffd06f44",
                      color: "#ffd06f",
                      fontSize: 13,
                      fontWeight: 600,
                      textTransform: "capitalize",
                    }}
                  >
                    {projectTone}
                  </span>
                </LabelRow>
              )}
              {projectThemes.length > 0 && (
                <LabelRow label="Themes">
                  <TagChips items={projectThemes} color="#6f7cff" />
                </LabelRow>
              )}
              {projectTags.length > 0 && (
                <LabelRow label="Tags">
                  <TagChips items={projectTags} color="#8ad6a2" />
                </LabelRow>
              )}
            </SectionCard>
          )}
        </>
      )}
    </div>
  );
}
