import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/apiClient";
import CreatePortfolioModal from "../components/update/Modal/CreatePortfolioModal";

type PortfolioListItem = {
  id: number;
  title: string;
  creation_time?: string;
  last_updated_at?: string;
  project_names?: string[];
};

type ListPortfoliosResponse = {
  portfolios: PortfolioListItem[];
};

function formatRelativeDate(value?: string | null) {
  if (!value) return "—";
  // Treat naive datetime strings (no timezone suffix) as UTC, since the
  // backend stores UTC datetimes without a 'Z' designator.
  const normalized = /[Zz]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return value;

  const now = Date.now();
  const diff = now - d.getTime();
  const minutes = Math.floor(diff / 60_000);
  const hours = Math.floor(diff / 3_600_000);
  const days = Math.floor(diff / 86_400_000);

  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function PortfoliosPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [portfolios, setPortfolios] = useState<PortfolioListItem[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const res = (await api.getPortfolios()) as ListPortfoliosResponse;
      setPortfolios(Array.isArray(res?.portfolios) ? res.portfolios : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load portfolios");
      setPortfolios([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleCreated(id: number) {
    setShowCreateModal(false);
    navigate(`/portfolios/${id}`);
  }

  return (
    <div style={{ padding: 24, paddingTop: 40, maxWidth: 800, margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 28,
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>Portfolios</h1>
          <p style={{ marginTop: 6, color: "var(--text-secondary)", margin: "6px 0 0" }}>
            Create and manage your portfolio showcases.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          style={{
            padding: "10px 18px",
            borderRadius: 10,
            border: "none",
            background: "var(--btn-primary)",
            color: "#fff",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Create Portfolio
        </button>
      </div>

      <CreatePortfolioModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={handleCreated}
      />

      {loading && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 20,
            background: "var(--bg-surface)",
            color: "var(--text-secondary)",
            fontSize: 14,
          }}
        >
          Loading portfolios...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            border: "1px solid var(--danger-bg-strong)",
            borderRadius: 14,
            padding: 20,
            background: "var(--danger-bg)",
            color: "var(--danger-text)",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && portfolios.length === 0 && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: 20,
            background: "var(--bg-surface)",
            color: "var(--text-muted)",
          }}
        >
          No portfolios yet. Click "Create Portfolio" to get started.
        </div>
      )}

      {!loading && !error && portfolios.length > 0 && (
        <div style={{ display: "grid", gap: 12 }}>
          {portfolios.map((p) => (
            <Link
              key={p.id}
              to={`/portfolios/${p.id}`}
              state={{ from: "/portfolios" }}
              style={{
                display: "block",
                textDecoration: "none",
                color: "inherit",
                border: "1px solid var(--border)",
                borderRadius: 14,
                padding: "18px 20px",
                background: "var(--bg-surface)",
                transition: "border-color 0.15s ease, background 0.15s ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--hover-border)";
                (e.currentTarget as HTMLElement).style.background = "var(--hover-bg)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                (e.currentTarget as HTMLElement).style.background = "var(--bg-surface)";
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 16,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Title */}
                  <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 10 }}>
                    {p.title || `Portfolio #${p.id}`}
                  </div>

                  {/* Project pills */}
                  {p.project_names && p.project_names.length > 0 ? (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                      {p.project_names.map((name) => (
                        <span
                          key={name}
                          style={{
                            padding: "3px 10px",
                            borderRadius: 999,
                            border: "1px solid #93c5fd",
                            background: "#dbeafe",
                            fontSize: 12,
                            color: "#0055B7",
                            fontWeight: 500,
                          }}
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 10 }}>
                      No projects
                    </div>
                  )}

                  {/* Last updated */}
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Updated {formatRelativeDate(p.last_updated_at)}
                  </div>
                </div>

                {/* Arrow */}
                <div style={{ color: "#444", fontSize: 18, flexShrink: 0, marginTop: 2 }}>
                  →
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
