import TipsAndUpdatesIcon from "@mui/icons-material/TipsAndUpdates";
import { useState } from "react";

interface HelpTooltipProps {
  text: string;
  size?: number;
}

export default function HelpTooltip({ text, size = 16 }: HelpTooltipProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center" }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <TipsAndUpdatesIcon
        style={{ fontSize: size, color: "var(--accent)", cursor: "help", display: "block" }}
      />
      {visible && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
            background: "#1e2030",
            color: "#f0f0f0",
            fontSize: 13,
            padding: "8px 12px",
            borderRadius: 9,
            width: 220,
            lineHeight: 1.5,
            zIndex: 9999,
            boxShadow: "0 6px 20px rgba(0,0,0,0.3)",
            pointerEvents: "none",
            textAlign: "left",
          }}
        >
          {text}
          <div
            style={{
              position: "absolute",
              top: "100%",
              left: "50%",
              transform: "translateX(-50%)",
              width: 0,
              height: 0,
              borderLeft: "6px solid transparent",
              borderRight: "6px solid transparent",
              borderTop: "6px solid #1e2030",
            }}
          />
        </div>
      )}
    </span>
  );
}
