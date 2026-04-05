// GitHub Linguist-style colors per language
export const LANG_COLOR_MAP: Record<string, string> = {
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

export const LANG_FALLBACK_COLORS = [
  "#6EC4E8", "#ff7c6f", "#7cff9a", "#ffd06f",
  "#c06fff", "#6fecff", "#ff6fb8", "#a8ff6f",
];

export function LanguageDonut({ langs }: { langs: Array<{ lang: string; ratio: number }> }) {
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
          <span style={{ fontSize: 10, color: "var(--text-secondary)", textAlign: "center", lineHeight: 1.3 }}>
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
            <span style={{ color: "var(--text-primary)", minWidth: 80 }}>{s.lang}</span>
            <span style={{ color: "var(--text-muted)" }}>{s.pct.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
