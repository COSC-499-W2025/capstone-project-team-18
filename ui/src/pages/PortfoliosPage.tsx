import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/apiClient";
import CreatePortfolioModal from "../components/update/modal/CreatePortfolioModal";

type PortfolioListItem = {
  id: number;
  title: string;
  creation_time?: string;
  last_updated_at?: string;
};

type ListPortfoliosResponse = {
  portfolios: PortfolioListItem[];
};

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
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
    <div style={{ padding: 24, paddingTop: 40 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>Portfolios</h1>
          <p style={{ marginTop: 8, color: "#666" }}>
            Create and manage your portfolio showcases.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          style={{ padding: "10px 14px" }}
        >
          Create Portfolio
        </button>
      </div>

      {loading && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
          }}
        >
          Loading portfolios...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            border: "1px solid #3a1f1f",
            borderRadius: 16,
            padding: 20,
            background: "#1a1111",
            color: "#ff8a8a",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && portfolios.length === 0 && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
            color: "#999",
          }}
        >
          No portfolios yet. Click "Create Portfolio" to get started.
        </div>
      )}

      {!loading && !error && portfolios.length > 0 && (
        <div style={{ display: "grid", gap: 16 }}>
          {portfolios.map((p) => (
            <Link
              key={p.id}
              to={`/portfolios/${p.id}`}
              style={{
                display: "block",
                textDecoration: "none",
                color: "inherit",
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                padding: 18,
                background: "#161616",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 20 }}>{p.title}</div>
                  <div style={{ fontSize: 13, color: "#999", marginTop: 8 }}>
                    Created: {formatDate(p.creation_time)}
                  </div>
                  <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                    Updated: {formatDate(p.last_updated_at)}
                  </div>
                </div>

              </div>
            </Link>
          ))}
        </div>
      )}

      <CreatePortfolioModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}
