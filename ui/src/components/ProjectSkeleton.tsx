function SkeletonBar({ width, height }: { width: string; height: number }) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius: 10,
        background:
          "linear-gradient(90deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.16) 50%, rgba(255,255,255,0.08) 100%)",
        backgroundSize: "200% 100%",
        animation: "project-skeleton-shimmer 1.4s ease-in-out infinite",
      }}
    />
  );
}

export default function ProjectSkeleton({ count = 3 }: { count?: number }) {
  return (
    <>
      <style>
        {`@keyframes project-skeleton-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }`}
      </style>
      <div style={{ display: "grid", gap: 12 }}>
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 12,
              padding: 14,
              background: "#101010",
              display: "grid",
              gap: 10,
            }}
          >
            <SkeletonBar width="75%" height={22} />
            <SkeletonBar width="45%" height={16} />
          </div>
        ))}
      </div>
    </>
  );
}
