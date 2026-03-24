import { useMemo, useState } from "react";

type SkillTimelineCounts = Record<string, Record<string, number>>;

type Point = {
  skill: string;
  date: string;
  count: number;
  x: number;
  y: number;
  r: number;
};

type SkillTimelineGraphProps = {
  data: SkillTimelineCounts;
};

const ACCENT_COLOR = "#E63946";

function formatDateLabel(date: string) {
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatTooltipDate(date: string) {
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    weekday: "short",
  });
}

export default function SkillTimelineGraph({ data }: SkillTimelineGraphProps) {
  const [hovered, setHovered] = useState<Point | null>(null);

  const model = useMemo(() => {
    const skills = Object.keys(data).filter((skill) => {
      const entries = Object.values(data[skill] ?? {});
      return entries.some((count) => count > 0);
    });

    if (skills.length === 0) return null;

    const sortedSkills = [...skills].sort((a, b) => {
      const totalA = Object.values(data[a] ?? {}).reduce((sum, v) => sum + v, 0);
      const totalB = Object.values(data[b] ?? {}).reduce((sum, v) => sum + v, 0);
      return totalB - totalA;
    });

    const allDates = new Set<string>();
    for (const skill of sortedSkills) {
      for (const [date, count] of Object.entries(data[skill] ?? {})) {
        if (count > 0) allDates.add(date);
      }
    }

    const sortedDates = Array.from(allDates).sort();
    if (sortedDates.length === 0) return null;

    const maxCount = Math.max(
      1,
      ...sortedSkills.flatMap((skill) => Object.values(data[skill] ?? {}))
    );

    const labelColumnWidth = 150;
    const plotLeftPad = 20;
    const rightPad = 28;
    const topPad = 20;
    const bottomPad = 40;
    const rowHeight = 40;
    const colWidth = 36;

    const width = plotLeftPad + rightPad + Math.max(sortedDates.length - 1, 1) * colWidth;
    const height = topPad + bottomPad + sortedSkills.length * rowHeight;

    const dateToX = (date: string) => {
      const index = sortedDates.indexOf(date);
      return plotLeftPad + index * colWidth;
    };

    const skillToY = (skill: string) => {
      const index = sortedSkills.indexOf(skill);
      return topPad + index * rowHeight + rowHeight / 2;
    };

    const points: Point[] = [];
    for (const skill of sortedSkills) {
      const byDate = data[skill] ?? {};
      for (const [date, count] of Object.entries(byDate)) {
        if (count <= 0) continue;

        const normalized = count / maxCount;
        const radius = 4 + normalized * 12;

        points.push({
          skill,
          date,
          count,
          x: dateToX(date),
          y: skillToY(skill),
          r: radius,
        });
      }
    }

    return {
      sortedSkills,
      sortedDates,
      points,
      width,
      height,
      labelColumnWidth,
      plotLeftPad,
      rightPad,
      topPad,
      bottomPad,
      rowHeight,
      maxCount,
      dateToX,
      skillToY,
    };
  }, [data]);

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

  return (
    <div
      style={{
        padding: 20,
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
          Skill Activity Timeline
        </h3>
        <span style={{ fontSize: 12, color: "#999" }}>
          Points scale based on usage
        </span>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "sticky",
            left: 0,
            zIndex: 2,
            width: model.labelColumnWidth,
            minWidth: model.labelColumnWidth,
            height: model.height,
            background: "#161616",
            borderRight: "1px solid #232323",
            paddingTop: model.topPad,
            paddingRight: 10,
            boxSizing: "border-box",
          }}
        >
          {model.sortedSkills.map((skill) => (
            <div
              key={`label-${skill}`}
              style={{
                height: model.rowHeight,
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                color: "#b8b8b8",
                fontSize: 11,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
              title={skill}
            >
              {skill}
            </div>
          ))}
        </div>

        <div style={{ overflowX: "auto", paddingBottom: 8, width: "100%" }}>
          <svg
            width={model.width}
            height={model.height}
            role="img"
            aria-label="Skill timeline graph"
          >
            {model.sortedSkills.map((skill) => {
              const y = model.skillToY(skill);
              return (
                <line
                  key={`row-${skill}`}
                  x1={model.plotLeftPad}
                  x2={model.width - model.rightPad}
                  y1={y}
                  y2={y}
                  stroke="#262626"
                  strokeWidth="1"
                />
              );
            })}

            {model.sortedDates.map((date, index) => {
              if (index % 3 !== 0 && index !== model.sortedDates.length - 1) return null;
              const x = model.dateToX(date);
              return (
                <g key={`date-${date}`}>
                  <line
                    x1={x}
                    x2={x}
                    y1={model.topPad - 4}
                    y2={model.height - model.bottomPad + 8}
                    stroke="#202020"
                    strokeWidth="1"
                  />
                  <text
                    x={x}
                    y={model.height - 10}
                    textAnchor="middle"
                    fill="#8f8f8f"
                    fontSize="10"
                  >
                    {formatDateLabel(date)}
                  </text>
                </g>
              );
            })}

            {model.points.map((p) => {
              const opacity = 0.25 + (p.count / model.maxCount) * 0.75;
              return (
                <circle
                  key={`${p.skill}-${p.date}`}
                  cx={p.x}
                  cy={p.y}
                  r={p.r}
                  fill={ACCENT_COLOR}
                  fillOpacity={opacity}
                  stroke={ACCENT_COLOR}
                  strokeWidth={hovered?.skill === p.skill && hovered?.date === p.date ? 2 : 1}
                  onMouseEnter={() => setHovered(p)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <title>{`${p.skill} • ${formatTooltipDate(p.date)} • ${p.count} occurrence${p.count === 1 ? "" : "s"}`}</title>
                </circle>
              );
            })}
          </svg>
        </div>
      </div>

      {hovered && (
        <div
          style={{
            marginTop: 10,
            borderRadius: 8,
            borderLeft: `3px solid ${ACCENT_COLOR}`,
            background: "#0f0f0f",
            color: "#e5e5e5",
            fontSize: 12,
            padding: "8px 10px",
          }}
        >
          {hovered.skill} on {formatTooltipDate(hovered.date)}: {hovered.count} occurrence
          {hovered.count === 1 ? "" : "s"}
        </div>
      )}
    </div>
  );
}
