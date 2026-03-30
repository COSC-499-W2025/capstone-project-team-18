import { useMemo, useState, useRef } from "react";
import type { MouseEvent } from "react";

type SkillTimelineCounts = Record<string, Record<string, number>>;

type SkillTimelineGraphProps = {
  data: SkillTimelineCounts;
  range?: {
    startDate: string | null;
    endDate: string | null;
  };
};

const TOP_SKILLS_LIMIT = 5;
const SKILL_COLORS = [
  "#002145", // UBC Blue (primary)
  "#5090AA", // Blue slate
  "#B09040", // Ochre
  "#5F8050", // Sage
  "#80506A", // Mauve
  "#2E7A72", // Teal
  "#9A5038", // Terracotta
  "#4B6490", // Slate blue
  "#8C6E30", // Warm tan
  "#6A3E90", // Soft purple
];

type TimelineBucket = {
  key: string;
  shortLabel: string;
  fullLabel: string;
};

function parseDateValue(value: string | null | undefined) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function toMonthStart(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function toMonthKey(date: Date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${date.getFullYear()}-${month}`;
}

function buildTimelineBuckets(startDate: Date, endDate: Date): TimelineBucket[] {
  const buckets: TimelineBucket[] = [];
  const start = toMonthStart(startDate);
  const end = toMonthStart(endDate);

  if (end < start) {
    return [
      {
        key: toMonthKey(start),
        shortLabel: start.toLocaleString(undefined, { month: "short", year: "2-digit" }),
        fullLabel: start.toLocaleString(undefined, { month: "short", year: "numeric" }),
      },
    ];
  }

  const cursor = new Date(start);
  while (cursor <= end) {
    buckets.push({
      key: toMonthKey(cursor),
      shortLabel: cursor.toLocaleString(undefined, { month: "short", year: "2-digit" }),
      fullLabel: cursor.toLocaleString(undefined, { month: "short", year: "numeric" }),
    });
    cursor.setMonth(cursor.getMonth() + 1);
  }

  return buckets;
}

function buildTickIndexes(length: number) {
  if (length <= 1) return [0];
  if (length <= 6) return Array.from({ length }, (_, index) => index);

  const desiredTicks = 6;
  const step = (length - 1) / (desiredTicks - 1);
  const indexes = new Set<number>([0, length - 1]);

  for (let tick = 1; tick < desiredTicks - 1; tick += 1) {
    indexes.add(Math.round(step * tick));
  }

  return Array.from(indexes).sort((a, b) => a - b);
}

function formatCountLabel(count: number) {
  return `${count} occurrence${count === 1 ? "" : "s"}`;
}

export default function SkillTimelineGraph({ data, range }: SkillTimelineGraphProps) {
  const [viewMode, setViewMode] = useState<"stacked" | "small-multiples">("stacked");
  const [hoveredMonth, setHoveredMonth] = useState<number | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const model = useMemo(() => {
    const monthlyCountsBySkill: Record<string, Record<string, number>> = {};
    const totalBySkill: Record<string, number> = {};
    let minActivityDate: Date | null = null;
    let maxActivityDate: Date | null = null;

    for (const [skill, byDate] of Object.entries(data)) {
      for (const [dateStr, rawCount] of Object.entries(byDate ?? {})) {
        const count = Number(rawCount ?? 0);
        if (!Number.isFinite(count) || count <= 0) continue;

        const parsed = new Date(dateStr);
        if (Number.isNaN(parsed.getTime())) continue;

        if (!minActivityDate || parsed < minActivityDate) minActivityDate = parsed;
        if (!maxActivityDate || parsed > maxActivityDate) maxActivityDate = parsed;

        if (!monthlyCountsBySkill[skill]) {
          monthlyCountsBySkill[skill] = {};
        }

        const monthKey = toMonthKey(parsed);
        monthlyCountsBySkill[skill][monthKey] =
          (monthlyCountsBySkill[skill][monthKey] ?? 0) + count;
        totalBySkill[skill] = (totalBySkill[skill] ?? 0) + count;
      }
    }

    const sortedSkills = Object.keys(totalBySkill).sort(
      (a, b) => (totalBySkill[b] ?? 0) - (totalBySkill[a] ?? 0)
    );

    if (sortedSkills.length === 0) return null;

    const providedStart = parseDateValue(range?.startDate);
    const providedEnd = parseDateValue(range?.endDate);
    const rangeStart = providedStart ?? minActivityDate;
    const rangeEnd = providedEnd ?? maxActivityDate;

    if (!rangeStart || !rangeEnd) return null;

    const timelineBuckets = buildTimelineBuckets(rangeStart, rangeEnd);
    const monthKeys = timelineBuckets.map((bucket) => bucket.key);
    const cumulativeBySkill: Record<string, number[]> = {};

    let globalMaxCumulative = 1;
    for (const skill of sortedSkills) {
      let runningTotal = 0;
      const cumulativeSeries = monthKeys.map((key) => {
        runningTotal += monthlyCountsBySkill[skill]?.[key] ?? 0;
        return runningTotal;
      });
      cumulativeBySkill[skill] = cumulativeSeries;
      const lastValue = cumulativeSeries[cumulativeSeries.length - 1] ?? 0;
      if (lastValue > globalMaxCumulative) globalMaxCumulative = lastValue;
    }

    return {
      sortedSkills,
      totalBySkill,
      cumulativeBySkill,
      timelineBuckets,
      globalMaxCumulative,
    };
  }, [data, range?.endDate, range?.startDate]);

  if (!model) {
    return (
      <div
        style={{
          padding: 20,
          border: "1px solid var(--border)",
          borderRadius: 12,
          background: "var(--bg-surface)",
          color: "#999",
          textAlign: "center",
        }}
      >
        No skill timeline data available
      </div>
    );
  }

  // Stacked view: all skills with >= 10 occurrences
  const stackedVisibleSkills = model.sortedSkills.filter(
    (skill) => (model.totalBySkill[skill] ?? 0) >= 10
  );
  // Small multiples view: top 5 with any occurrences
  const smallMultiplesVisibleSkills = model.sortedSkills
    .filter((skill) => (model.totalBySkill[skill] ?? 0) > 0)
    .slice(0, TOP_SKILLS_LIMIT);

  const visibleSkills =
    viewMode === "stacked" ? stackedVisibleSkills : smallMultiplesVisibleSkills;

  if (visibleSkills.length === 0) {
    return (
      <div
        style={{
          padding: 20,
          border: "1px solid var(--border)",
          borderRadius: 12,
          background: "var(--bg-surface)",
          color: "#999",
          textAlign: "center",
        }}
      >
        No skill timeline data available
      </div>
    );
  }

  // ---- Stacked area chart helpers ----
  const n = model.timelineBuckets.length;

  const globalMaxIndividual = Math.max(
    1,
    ...visibleSkills.map((skill) => model.cumulativeBySkill[skill]?.[n - 1] ?? 0)
  );

  const indivLogNorm = (v: number) =>
    Math.log(1 + v) / Math.log(1 + globalMaxIndividual);

  const logStackedSeries: number[][] = [];
  for (let k = 0; k < visibleSkills.length; k++) {
    const logSeries = (model.cumulativeBySkill[visibleSkills[k]] ?? []).map(indivLogNorm);
    logStackedSeries.push(
      k === 0
        ? [...logSeries]
        : logSeries.map((v, i) => v + (logStackedSeries[k - 1]![i] ?? 0))
    );
  }

  const totalLogHeight = Math.max(
    1,
    logStackedSeries[logStackedSeries.length - 1]?.[n - 1] ?? 1
  );

  const SVG_W = 760;
  const SVG_H = 380;
  const L = 8, R = 8, T = 12, B = 30;
  const CW = SVG_W - L - R;
  const CH = SVG_H - T - B;

  const xAt = (i: number) => L + (i / Math.max(1, n - 1)) * CW;
  const yAt = (logV: number) => T + (1 - logV / totalLogHeight) * CH;

  const tickIdxs = buildTickIndexes(n);

  function handleMouseMove(e: MouseEvent<SVGSVGElement>) {
    if (!containerRef.current) return;
    const ctm = e.currentTarget.getScreenCTM();
    if (!ctm) return;
    const svgX = (e.clientX - ctm.e) / ctm.a;
    const frac = Math.max(0, Math.min(1, (svgX - L) / CW));
    setHoveredMonth(Math.round(frac * Math.max(0, n - 1)));
    const cRect = containerRef.current.getBoundingClientRect();
    setTooltipPos({ x: e.clientX - cRect.left, y: e.clientY - cRect.top });
  }

  function handleMouseLeave() {
    setHoveredMonth(null);
    setTooltipPos(null);
  }

  const tooltipWidth = 170;
  const containerWidth = containerRef.current?.offsetWidth ?? 600;
  const tipLeft =
    tooltipPos !== null && tooltipPos.x + 16 + tooltipWidth > containerWidth
      ? tooltipPos.x - tooltipWidth - 8
      : (tooltipPos?.x ?? 0) + 16;

  return (
    <div
      ref={containerRef}
      style={{
        padding: 28,
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--bg-surface)",
        position: "relative",
      }}
    >
      {/* Header with toggle */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
          Most Utilized Skills
        </h3>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            onClick={() => setViewMode("stacked")}
            style={{
              padding: "4px 12px",
              fontSize: 12,
              borderRadius: "6px 0 0 6px",
              border: "1px solid var(--border)",
              background: viewMode === "stacked" ? "var(--accent)" : "transparent",
              color: viewMode === "stacked" ? "#fff" : "#888",
              cursor: "pointer",
              fontWeight: viewMode === "stacked" ? 600 : 400,
            }}
          >
            Stacked
          </button>
          <button
            onClick={() => setViewMode("small-multiples")}
            style={{
              padding: "4px 12px",
              fontSize: 12,
              borderRadius: "0 6px 6px 0",
              border: "1px solid var(--border)",
              borderLeft: "none",
              background: viewMode === "small-multiples" ? "var(--accent)" : "transparent",
              color: viewMode === "small-multiples" ? "#fff" : "#888",
              cursor: "pointer",
              fontWeight: viewMode === "small-multiples" ? 600 : 400,
            }}
          >
            Individual
          </button>
        </div>
      </div>

      <p style={{ margin: "0 0 12px 0", fontSize: 12, color: "#999" }}>
        Cumulative running total of skill occurrences across all projects, plotted continuously from the earliest to latest project date.
      </p>

      {/* ---- STACKED VIEW ---- */}
      {viewMode === "stacked" && (
        <>
          {/* Legend */}
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 14 }}>
            {visibleSkills.map((skill, k) => (
              <div key={skill} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 2,
                    background: SKILL_COLORS[k % SKILL_COLORS.length],
                    flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: 12, color: "#444" }}>{skill}</span>
                <span style={{ fontSize: 11, color: "#666" }}>
                  ({model.totalBySkill[skill] ?? 0})
                </span>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div
            style={{
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "var(--bg-surface)",
              padding: "10px 4px 4px",
            }}
          >
            <svg
              width="100%"
              height={SVG_H}
              viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              style={{ display: "block" }}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
              role="img"
              aria-label="Stacked cumulative skill activity"
            >
              {[0.25, 0.5, 0.75, 1].map((ratio) => (
                <line
                  key={`grid-${ratio}`}
                  x1={L}
                  x2={SVG_W - R}
                  y1={T + CH * (1 - ratio)}
                  y2={T + CH * (1 - ratio)}
                  stroke="var(--border)"
                  strokeWidth="1"
                />
              ))}

              {visibleSkills.map((skill, k) => {
                const topLogSeries = logStackedSeries[k] ?? [];
                const botLogSeries =
                  k === 0 ? new Array(n).fill(0) : (logStackedSeries[k - 1] ?? []);
                const color = SKILL_COLORS[k % SKILL_COLORS.length];

                const topPts = topLogSeries.map(
                  (v, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(v)}`
                );
                const botPts = [...botLogSeries]
                  .reverse()
                  .map((v, ri) => `L ${xAt(n - 1 - ri)} ${yAt(v)}`);
                const areaD = [...topPts, ...botPts, "Z"].join(" ");
                const lineD = topLogSeries
                  .map((v, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(v)}`)
                  .join(" ");

                return (
                  <g key={`band-${skill}`}>
                    <path d={areaD} fill={color} fillOpacity="0.75" />
                    <path
                      d={lineD}
                      fill="none"
                      stroke={color}
                      strokeWidth="1.2"
                      strokeOpacity="0.9"
                    />
                  </g>
                );
              })}

              {hoveredMonth !== null && (
                <line
                  x1={xAt(hoveredMonth)}
                  y1={T}
                  x2={xAt(hoveredMonth)}
                  y2={T + CH}
                  stroke="var(--border-strong)"
                  strokeWidth="1"
                  strokeOpacity="0.6"
                  strokeDasharray="3 3"
                />
              )}

              {tickIdxs.map((mi) => (
                <text
                  key={`tick-${mi}`}
                  x={xAt(mi)}
                  y={SVG_H - 6}
                  textAnchor="middle"
                  fill="#7f7f7f"
                  fontSize="9"
                >
                  {model.timelineBuckets[mi]?.shortLabel ?? ""}
                </text>
              ))}
            </svg>
          </div>

          {/* Floating tooltip */}
          {hoveredMonth !== null && tooltipPos !== null && (
            <div
              style={{
                position: "absolute",
                left: tipLeft,
                top: Math.max(8, tooltipPos.y - 16),
                background: "var(--bg-surface-deep)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "8px 12px",
                pointerEvents: "none",
                zIndex: 20,
                width: tooltipWidth,
                boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#888",
                  marginBottom: 6,
                  paddingBottom: 5,
                  borderBottom: "1px solid var(--border)",
                  whiteSpace: "nowrap",
                }}
              >
                {model.timelineBuckets[hoveredMonth]?.fullLabel ?? ""}
              </div>
              {visibleSkills.map((skill, k) => {
                const count = model.cumulativeBySkill[skill]?.[hoveredMonth] ?? 0;
                if (count === 0) return null;
                return (
                  <div
                    key={skill}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 7,
                      marginBottom: 3,
                    }}
                  >
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 2,
                        background: SKILL_COLORS[k % SKILL_COLORS.length],
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontSize: 11,
                        color: "#555",
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {skill}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        color: "var(--text-primary)",
                        fontVariantNumeric: "tabular-nums",
                        flexShrink: 0,
                      }}
                    >
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ---- SMALL MULTIPLES VIEW ---- */}
      {viewMode === "small-multiples" && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(400px, 400px))",
            justifyContent: "start",
            columnGap: 28,
            rowGap: 26,
            paddingTop: 8,
          }}
        >
          {visibleSkills.map((skill, index) => {
            const cumulativeSeries = model.cumulativeBySkill[skill] ?? [];
            const timelineTotal = model.totalBySkill[skill] ?? 0;
            const maxValue = model.globalMaxCumulative;
            const color = SKILL_COLORS[index % SKILL_COLORS.length];

            const width = 400;
            const height = 140;
            const leftPad = 10;
            const rightPad = 10;
            const topPad = 12;
            const bottomPad = 22;
            const chartWidth = width - leftPad - rightPad;
            const chartHeight = height - topPad - bottomPad;
            const tickIndexes = buildTickIndexes(cumulativeSeries.length);

            const xForIndex = (monthIndex: number) =>
              leftPad + (monthIndex / Math.max(1, cumulativeSeries.length - 1)) * chartWidth;
            const logScale = (value: number) =>
              maxValue <= 1 ? value / maxValue : Math.log(1 + value) / Math.log(1 + maxValue);
            const yForValue = (value: number) =>
              topPad + (1 - logScale(value)) * chartHeight;

            const linePath = cumulativeSeries
              .map((value, monthIndex) => {
                const x = xForIndex(monthIndex);
                const y = yForValue(value);
                return `${monthIndex === 0 ? "M" : "L"} ${x} ${y}`;
              })
              .join(" ");

            const areaPath = `${linePath} L ${xForIndex(cumulativeSeries.length - 1)} ${topPad + chartHeight} L ${xForIndex(0)} ${topPad + chartHeight} Z`;

            return (
              <div
                key={`small-multiple-${skill}`}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  background: "var(--bg-surface)",
                  padding: 18,
                  borderTop: `3px solid ${color}`,
                  width: "400px",
                  maxWidth: "100%",
                  boxSizing: "border-box",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 8,
                  }}
                >
                  <div
                    style={{
                      color: "var(--text-primary)",
                      fontSize: 13,
                      fontWeight: 700,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={skill}
                  >
                    {skill}
                  </div>
                  <div style={{ color: "#989898", fontSize: 11 }}>
                    {formatCountLabel(timelineTotal)}
                  </div>
                </div>

                <svg
                  width="100%"
                  height={height}
                  viewBox={`0 0 ${width} ${height}`}
                  role="img"
                  aria-label={`${skill} cumulative activity`}
                  style={{ display: "block" }}
                >
                  {[0.25, 0.5, 0.75, 1].map((ratio) => {
                    const y = topPad + chartHeight * (1 - ratio);
                    return (
                      <line
                        key={`grid-${skill}-${ratio}`}
                        x1={leftPad}
                        x2={width - rightPad}
                        y1={y}
                        y2={y}
                        stroke="var(--border)"
                        strokeWidth="1"
                      />
                    );
                  })}

                  <path d={areaPath} fill={color} fillOpacity="0.2" />
                  <path d={linePath} fill="none" stroke={color} strokeWidth="2" />

                  {cumulativeSeries.map((value, monthIndex) => (
                    <circle
                      key={`dot-${skill}-${monthIndex}`}
                      cx={xForIndex(monthIndex)}
                      cy={yForValue(value)}
                      r={2.4}
                      fill={color}
                      stroke="var(--bg-surface)"
                      strokeWidth="0.6"
                    >
                      <title>{`${model.timelineBuckets[monthIndex]?.fullLabel ?? ""}: ${formatCountLabel(value)} cumulative`}</title>
                    </circle>
                  ))}

                  {tickIndexes.map((monthIndex) => (
                    <text
                      key={`month-${skill}-${monthIndex}`}
                      x={xForIndex(monthIndex)}
                      y={height - 6}
                      textAnchor="middle"
                      fill="#7f7f7f"
                      fontSize="9"
                    >
                      {model.timelineBuckets[monthIndex]?.shortLabel ?? ""}
                    </text>
                  ))}
                </svg>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
