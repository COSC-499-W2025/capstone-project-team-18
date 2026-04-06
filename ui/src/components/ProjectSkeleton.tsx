function SkeletonBar({ width, height }: { width: string; height: number }) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius: 10,
        background:
          "linear-gradient(90deg, #e8e8e8 0%, #d0d0d0 50%, #e8e8e8 100%)",
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
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 14,
              background: "#f0f0f0",
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
