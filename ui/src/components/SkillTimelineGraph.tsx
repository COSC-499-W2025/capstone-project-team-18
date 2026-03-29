import { useMemo } from "react";

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
  "#E63946", // Ruby red
  "#7A9BA8", // Muted blue slate
  "#A89B6B", // Muted ochre
  "#7B8B6F", // Muted sage
  "#8B6B7A", // Muted mauve
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
          border: "1px solid #2a2a2a",
          borderRadius: 12,
          background: "#161616",
          color: "#999",
          textAlign: "center",
        }}
      >
        No skill timeline data available
      </div>
    );
  }

  const visibleSkills = model.sortedSkills
    .filter((skill) => (model.totalBySkill[skill] ?? 0) > 0)
    .slice(0, TOP_SKILLS_LIMIT);

  return (
    <div
      style={{
        padding: 28,
        border: "1px solid #2a2a2a",
        borderRadius: 12,
        background: "#161616",
      }}
    >
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
      </div>

      <p style={{ margin: "0 0 14px 0", fontSize: 12, color: "#999" }}>
        Cumulative running total of skill occurrences across all projects, plotted continuously from the earliest to latest project date.
      </p>

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
                border: "1px solid #2a2a2a",
                borderRadius: 10,
                background: "#121212",
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
                    color: "#e8e8e8",
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
                      stroke="#1f1f1f"
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
                    stroke="#121212"
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
    </div>
  );
}
