import { useEffect, useState } from "react";
import { api } from "../api/apiClient";

type SkillsResponse = {
  skills: unknown[];
};

export default function SkillsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [skills, setSkills] = useState<unknown[]>([]);

  async function load() {
    try {
      setLoading(true);
      setError(null);

      const res = (await api.getSkills()) as SkillsResponse;
      setSkills(Array.isArray(res?.skills) ? res.skills : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load skills");
      setSkills([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h1 style={{ marginTop: 0, marginBottom: 0 }}>Skills</h1>
        <button onClick={load} disabled={loading} style={{ padding: "6px 10px" }}>
          Refresh
        </button>
      </div>

      <p style={{ marginTop: 8, color: "#666" }}>
        Data from <code>GET /skills</code>.
      </p>

      {loading && <div>Loading skills…</div>}

      {!loading && error && (
        <div style={{ color: "crimson" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && skills.length === 0 && (
        <div>No skills found.</div>
      )}
    </div>
  );
}