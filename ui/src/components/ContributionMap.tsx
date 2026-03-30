import { useEffect, useMemo, useState } from "react";

type ViewMode = "personal" | "ratio";

interface ContributionMapProps {
  personalTimeline: Record<string, number>; // { "2024-03-01": 3, ... }
  totalTimeline: Record<string, number>;   // { "2024-03-01": 10, ... }
}

// Ruby red accent color
const ACCENT_COLOR = "#002145";

/**
 * GitHub-style contribution map with two views:
 * 1. Personal: opacity based on personal commits (relative to max)
 * 2. Ratio: opacity based on user's % of total team activity
 */
export default function ContributionMap({
  personalTimeline,
  totalTimeline,
}: ContributionMapProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("personal");
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);

  const availableYears = useMemo(() => {
    const years = new Set<number>();
    for (const date of [...Object.keys(personalTimeline), ...Object.keys(totalTimeline)]) {
      const year = Number(date.slice(0, 4));
      if (!Number.isNaN(year)) {
        years.add(year);
      }
    }
    return Array.from(years).sort((a, b) => a - b);
  }, [personalTimeline, totalTimeline]);

  useEffect(() => {
    if (availableYears.length === 0) {
      setSelectedYear(null);
      return;
    }

    setSelectedYear((prev) =>
      prev && availableYears.includes(prev)
        ? prev
        : availableYears[availableYears.length - 1]
    );
  }, [availableYears]);

  // Generate list of dates for the selected year
  const dateRange = useMemo(() => {
    if (!selectedYear) return [];

    const startDate = new Date(selectedYear, 0, 1);
    const endDate = new Date(selectedYear, 11, 31);
    const dates: string[] = [];

    const current = new Date(startDate);
    while (current <= endDate) {
      const year = current.getFullYear();
      const month = String(current.getMonth() + 1).padStart(2, "0");
      const day = String(current.getDate()).padStart(2, "0");
      dates.push(`${year}-${month}-${day}`);
      current.setDate(current.getDate() + 1);
    }

    return dates;
  }, [selectedYear]);

  const goToPreviousYear = () => {
    if (availableYears.length === 0 || selectedYear == null) return;

    const currentIndex = availableYears.indexOf(selectedYear);
    if (currentIndex <= 0) return;
    setSelectedYear(availableYears[currentIndex - 1]);
    setHoveredDate(null);
  };

  const goToNextYear = () => {
    if (availableYears.length === 0 || selectedYear == null) return;

    const currentIndex = availableYears.indexOf(selectedYear);
    if (currentIndex === -1 || currentIndex >= availableYears.length - 1) return;
    setSelectedYear(availableYears[currentIndex + 1]);
    setHoveredDate(null);
  };

  const selectedYearIndex = selectedYear == null ? -1 : availableYears.indexOf(selectedYear);
  const canGoPreviousYear = selectedYearIndex > 0;
  const canGoNextYear = selectedYearIndex !== -1 && selectedYearIndex < availableYears.length - 1;

  // Calculate opacity for personal view
  const getPersonalOpacity = (date: string): number => {
    const count = personalTimeline[date] ?? 0;
    if (count === 0) return 0;

    const maxCount = Math.max(...Object.values(personalTimeline), 1);
    return Math.max(0.1, count / maxCount);
  };

  // Calculate opacity for ratio view
  const getRatioOpacity = (date: string): number => {
    const userCount = personalTimeline[date] ?? 0;
    const totalCount = totalTimeline[date] ?? 0;

    if (userCount === 0 || totalCount === 0) return 0;

    const ratio = userCount / totalCount;
    // Find max ratio to normalize
    const maxRatio = Math.max(
      ...dateRange.map((d) => {
        const u = personalTimeline[d] ?? 0;
        const t = totalTimeline[d] ?? 0;
        return t > 0 ? u / t : 0;
      }),
      0.1
    );

    return Math.max(0.1, (ratio / maxRatio));
  };

  const getOpacity = (date: string): number => {
    return viewMode === "personal"
      ? getPersonalOpacity(date)
      : getRatioOpacity(date);
  };

  const getTooltipText = (date: string): string => {
    const userCount = personalTimeline[date] ?? 0;
    const totalCount = totalTimeline[date] ?? 0;

    if (userCount === 0) return "";

    const dateObj = new Date(date);
    const displayDate = Number.isNaN(dateObj.getTime())
      ? date
      : dateObj.toLocaleDateString("en-US", {
          month: "long",
          day: "numeric",
          year: "numeric",
        });

    if (viewMode === "personal") {
      return `${displayDate}: ${userCount} commit${userCount !== 1 ? "s" : ""}`;
    } else {
      const percentage = totalCount > 0
        ? ((userCount / totalCount) * 100).toFixed(1)
        : "0";
      return `${displayDate}: ${userCount}/${totalCount} commits (${percentage}% of team activity)`;
    }
  };

  // Group dates by week
  const weeks = useMemo(() => {
    const result: string[][] = [];
    let currentWeek: string[] = [];

    for (const date of dateRange) {
      const dateObj = new Date(date);
      const dayOfWeek = dateObj.getDay();

      if (dayOfWeek === 0 && currentWeek.length > 0) {
        result.push(currentWeek);
        currentWeek = [];
      }
      currentWeek.push(date);
    }

    if (currentWeek.length > 0) {
      result.push(currentWeek);
    }

    return result;
  }, [dateRange]);

  if (dateRange.length === 0) {
    return (
      <div
        style={{
          padding: 20,
          border: "1px solid var(--border)",
          borderRadius: 12,
          background: "var(--bg-surface)",
          color: "var(--text-muted)",
          textAlign: "center",
        }}
      >
        No contribution data available
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 20,
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--bg-surface)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
          Contribution Map
        </h3>

        {/* Toggle buttons */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setViewMode("personal")}
            style={{
              padding: "8px 12px",
              background: viewMode === "personal" ? ACCENT_COLOR : "transparent",
              border: `1px solid ${ACCENT_COLOR}`,
              borderRadius: 8,
              color: viewMode === "personal" ? "#fff" : ACCENT_COLOR,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 500,
              transition: "all 0.2s",
            }}
          >
            Personal
          </button>
          <button
            onClick={() => setViewMode("ratio")}
            style={{
              padding: "8px 12px",
              background: viewMode === "ratio" ? ACCENT_COLOR : "transparent",
              border: `1px solid ${ACCENT_COLOR}`,
              borderRadius: 8,
              color: viewMode === "ratio" ? "#fff" : ACCENT_COLOR,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 500,
              transition: "all 0.2s",
            }}
          >
            Ratio View
          </button>
        </div>
      </div>

      {/* View description */}
      <p style={{ margin: "0 0 16px 0", fontSize: 12, color: "var(--text-muted)" }}>
        {viewMode === "personal"
          ? "Contribution activity as a function of commits"
          : "Shows your activity as a percentage of total team contributions"}
      </p>

      {/* Contribution grid */}
      <div
        style={{
          display: "flex",
          gap: 4,
          overflowX: "auto",
          paddingBottom: 8,
        }}
      >
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {week.map((date) => {
              const opacity = getOpacity(date);
              const bgColor =
                opacity === 0
                  ? "#e8e8e8"
                  : `rgba(0, 33, 69, ${opacity})`;

              return (
                <div
                  key={date}
                  onMouseEnter={() => setHoveredDate(date)}
                  onMouseLeave={() => setHoveredDate(null)}
                  style={{
                    width: 12,
                    height: 12,
                    background: bgColor,
                    borderRadius: 2,
                    cursor: "pointer",
                    border: hoveredDate === date ? `1px solid ${ACCENT_COLOR}` : "1px solid transparent",
                    transition: "all 0.2s",
                    position: "relative",
                  }}
                  title={getTooltipText(date)}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div
        style={{
          marginTop: 16,
          paddingTop: 12,
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: 11,
          color: "var(--text-muted)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span>Less</span>
          <div style={{ display: "flex", gap: 2 }}>
            {[0, 0.25, 0.5, 0.75, 1].map((opacity, i) => (
              <div
                key={i}
                style={{
                  width: 10,
                  height: 10,
                  background:
                    opacity === 0
                      ? "#e8e8e8"
                      : `rgba(0, 33, 69, ${opacity})`,
                  borderRadius: 2,
                }}
              />
            ))}
          </div>
          <span>More</span>
        </div>

        {selectedYear && (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
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
        )}
      </div>

      {/* Hovered date info */}
      {hoveredDate && getTooltipText(hoveredDate) && (
        <div
          style={{
            marginTop: 12,
            padding: 8,
            background: "var(--bg-surface-deep)",
            borderRadius: 6,
            fontSize: 12,
            color: ACCENT_COLOR,
            borderLeft: `3px solid ${ACCENT_COLOR}`,
          }}
        >
          {getTooltipText(hoveredDate)}
        </div>
      )}
    </div>
  );
}
