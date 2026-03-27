import { useEffect, useMemo, useState } from "react";

type SkillTimelineCounts = Record<string, Record<string, number>>;

type SkillTimelineGraphProps = {
  data: SkillTimelineCounts;
};

const ACCENT_COLOR = "#E63946";
const TOP_SKILLS_LIMIT = 5;
const SKILL_COLORS = [
  "#E63946", // Ruby red
  "#7A9BA8", // Muted blue slate
  "#A89B6B", // Muted ochre
  "#7B8B6F", // Muted sage
  "#8B6B7A", // Muted mauve
];

function buildMonthLabel(index: number) {
  return new Date(2024, index, 1).toLocaleString(undefined, { month: "short" });
}

function formatCountLabel(count: number) {
  return `${count} occurrence${count === 1 ? "" : "s"}`;
}

export default function SkillTimelineGraph({ data }: SkillTimelineGraphProps) {
  const [selectedYear, setSelectedYear] = useState<number | null>(null);

  const model = useMemo(() => {
    const monthlyBySkillYear: Record<string, Record<number, number[]>> = {};
    const totalBySkill: Record<string, number> = {};
    const years = new Set<number>();

    for (const [skill, byDate] of Object.entries(data)) {
      for (const [dateStr, rawCount] of Object.entries(byDate ?? {})) {
        const count = Number(rawCount ?? 0);
        if (!Number.isFinite(count) || count <= 0) continue;

        const parsed = new Date(dateStr);
        if (Number.isNaN(parsed.getTime())) continue;

        const year = parsed.getFullYear();
        const month = parsed.getMonth();

        years.add(year);

        if (!monthlyBySkillYear[skill]) {
          monthlyBySkillYear[skill] = {};
        }
        if (!monthlyBySkillYear[skill][year]) {
          monthlyBySkillYear[skill][year] = new Array(12).fill(0);
        }

        monthlyBySkillYear[skill][year][month] += count;
        totalBySkill[skill] = (totalBySkill[skill] ?? 0) + count;
      }
    }

    const sortedSkills = Object.keys(totalBySkill).sort(
      (a, b) => (totalBySkill[b] ?? 0) - (totalBySkill[a] ?? 0)
    );

    if (sortedSkills.length === 0) return null;

    let globalMaxMonthly = 1;
    for (const byYear of Object.values(monthlyBySkillYear)) {
      for (const monthlySeries of Object.values(byYear)) {
        for (const value of monthlySeries) {
          if (value > globalMaxMonthly) {
            globalMaxMonthly = value;
          }
        }
      }
    }

    return {
      sortedSkills,
      totalBySkill,
      monthlyBySkillYear,
      years: Array.from(years).sort((a, b) => a - b),
      globalMaxMonthly,
    };
  }, [data]);

  useEffect(() => {
    if (!model || model.years.length === 0) {
      setSelectedYear(null);
      return;
    }

    setSelectedYear((prev) =>
      prev && model.years.includes(prev)
        ? prev
        : model.years[model.years.length - 1]
    );
  }, [model]);

  if (!model || !selectedYear) {
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

  const selectedYearIndex = model.years.indexOf(selectedYear);
  const canGoPreviousYear = selectedYearIndex > 0;
  const canGoNextYear = selectedYearIndex !== -1 && selectedYearIndex < model.years.length - 1;

  const visibleSkills = model.sortedSkills
    .map((skill) => {
      const monthlySeries = model.monthlyBySkillYear[skill]?.[selectedYear] ?? new Array(12).fill(0);
      const yearlyTotal = monthlySeries.reduce((sum, value) => sum + value, 0);
      return { skill, yearlyTotal };
    })
    .filter((entry) => entry.yearlyTotal > 0)
    .sort((a, b) => b.yearlyTotal - a.yearlyTotal)
    .slice(0, TOP_SKILLS_LIMIT)
    .map((entry) => entry.skill);

  const goToPreviousYear = () => {
    if (!canGoPreviousYear) return;
    setSelectedYear(model.years[selectedYearIndex - 1]);
  };

  const goToNextYear = () => {
    if (!canGoNextYear) return;
    setSelectedYear(model.years[selectedYearIndex + 1]);
  };

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
        Daily activity is grouped into monthly trend charts for the selected year.
      </p>

      <div
        style={{
          marginBottom: 14,
          padding: "10px 0 0 0",
          borderTop: "1px solid #2a2a2a",
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 6,
        }}
      >
        <button
          onClick={goToPreviousYear}
          disabled={!canGoPreviousYear}
          style={{
            padding: "6px 10px",
            background: "transparent",
            border: `1px solid ${canGoPreviousYear ? ACCENT_COLOR : "#444"}`,
            borderRadius: 8,
            color: canGoPreviousYear ? ACCENT_COLOR : "#666",
            cursor: canGoPreviousYear ? "pointer" : "not-allowed",
            fontSize: 11,
            fontWeight: 600,
          }}
          title="Previous year"
        >
          ←
        </button>

        <div
          style={{
            minWidth: 70,
            textAlign: "center",
            fontSize: 11,
            fontWeight: 600,
            color: ACCENT_COLOR,
          }}
        >
          {selectedYear}
        </div>

        <button
          onClick={goToNextYear}
          disabled={!canGoNextYear}
          style={{
            padding: "6px 10px",
            background: "transparent",
            border: `1px solid ${canGoNextYear ? ACCENT_COLOR : "#444"}`,
            borderRadius: 8,
            color: canGoNextYear ? ACCENT_COLOR : "#666",
            cursor: canGoNextYear ? "pointer" : "not-allowed",
            fontSize: 11,
            fontWeight: 600,
          }}
          title="Next year"
        >
          →
        </button>
      </div>

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
          const monthlySeries = model.monthlyBySkillYear[skill]?.[selectedYear] ?? new Array(12).fill(0);
          const yearlyTotal = monthlySeries.reduce((sum, value) => sum + value, 0);
          const maxValue = model.globalMaxMonthly;
          const color = SKILL_COLORS[index % SKILL_COLORS.length];

          const width = 400;
          const height = 140;
          const leftPad = 10;
          const rightPad = 10;
          const topPad = 12;
          const bottomPad = 22;
          const chartWidth = width - leftPad - rightPad;
          const chartHeight = height - topPad - bottomPad;

          const xForIndex = (monthIndex: number) =>
            leftPad + (monthIndex / (monthlySeries.length - 1)) * chartWidth;
          const yForValue = (value: number) =>
            topPad + (1 - value / maxValue) * chartHeight;

          const linePath = monthlySeries
            .map((value, monthIndex) => {
              const x = xForIndex(monthIndex);
              const y = yForValue(value);
              return `${monthIndex === 0 ? "M" : "L"} ${x} ${y}`;
            })
            .join(" ");

          const areaPath = `${linePath} L ${xForIndex(monthlySeries.length - 1)} ${topPad + chartHeight} L ${xForIndex(0)} ${topPad + chartHeight} Z`;

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
                  {formatCountLabel(yearlyTotal)}
                </div>
              </div>

              <svg
                width="100%"
                height={height}
                viewBox={`0 0 ${width} ${height}`}
                role="img"
                aria-label={`${skill} monthly activity`}
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

                {monthlySeries.map((value, monthIndex) => (
                  <circle
                    key={`dot-${skill}-${monthIndex}`}
                    cx={xForIndex(monthIndex)}
                    cy={yForValue(value)}
                    r={2.4}
                    fill={color}
                    stroke="#121212"
                    strokeWidth="0.6"
                  >
                    <title>{`${buildMonthLabel(monthIndex)} ${selectedYear}: ${formatCountLabel(value)}`}</title>
                  </circle>
                ))}

                {[0, 3, 6, 9, 11].map((monthIndex) => (
                  <text
                    key={`month-${skill}-${monthIndex}`}
                    x={xForIndex(monthIndex)}
                    y={height - 6}
                    textAnchor="middle"
                    fill="#7f7f7f"
                    fontSize="9"
                  >
                    {buildMonthLabel(monthIndex)}
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
