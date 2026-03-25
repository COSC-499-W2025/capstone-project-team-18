import { Skeleton } from "@mui/material";

export default function ProjectSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 12,
            padding: 14,
            background: "#101010",
          }}
        >
          <Skeleton
            variant="rounded"
            width="75%"
            height={22}
            animation="wave"
            sx={{ bgcolor: "rgba(255,255,255,0.14)" }}
          />
          <Skeleton
            variant="rounded"
            width="45%"
            height={16}
            animation="wave"
            sx={{ bgcolor: "rgba(255,255,255,0.10)", mt: 1 }}
          />
        </div>
      ))}
    </div>
  );
}