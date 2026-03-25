import { useEffect, useState } from "react";
import { api } from "../api/apiClient";

type WeightedSkill = {
  name: string;
  weight: number;
};

type SkillsResponse = {
  skills: WeightedSkill[];
};

export default function SkillsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detectedSkills, setDetectedSkills] = useState<WeightedSkill[]>([]);
  const [userSkills, setUserSkills] = useState<string[]>([]);


  async function load() {
    try {
      setLoading(true);
      setError(null);

      const [skillsRes, configRes] = await Promise.all([
        api.getSkills() as Promise<SkillsResponse>,
        api.getUserConfig(),
      ]);

      setDetectedSkills(Array.isArray(skillsRes?.skills) ? skillsRes.skills : []);
      setUserSkills(configRes?.resume_config?.skills ?? []);

    } catch (e: any) {
      setError(e?.message ?? "Failed to load skills");
      setDetectedSkills([]);
      setUserSkills([]);

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

      {loading && <div>Loading skills…</div>}

      {!loading && error && (
        <div style={{ color: "crimson" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <section style={{ marginTop: 24 }}>
            <h2 style={{ marginBottom: 8, fontSize: 18 }}>Your Skills</h2>
            <p style={{ color: "#666", marginTop: 0, fontSize: 13 }}>
              Manually added via Profile. Used in resume generation.
            </p>
            {userSkills.length === 0 ? (
              <div style={{ color: "#888" }}>
                No skills added yet. Add them in{" "}
                <strong>Profile → Skills</strong>.
              </div>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {userSkills.map((skill, i) => (
                  <span
                    key={i}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 20,
                      background: "#1a1a1a",
                      border: "1px solid #2a2a2a",
                      fontSize: 13,
                      color: "#ddd",
                    }}
                  >
                    {skill}
                  </span>
                ))}
              </div>
            )}
          </section>

          <section style={{ marginTop: 32 }}>
            <h2 style={{ marginBottom: 8, fontSize: 18 }}>Detected Skills</h2>
            <p style={{ color: "#666", marginTop: 0, fontSize: 13 }}>
              Auto-extracted from your mined projects.
            </p>
            {detectedSkills.length === 0 ? (
              <div style={{ color: "#888" }}>
                No detected skills yet. Mine a project to populate this list.
              </div>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {detectedSkills
                  .slice()
                  .sort((a, b) => b.weight - a.weight)
                  .map((skill, i) => (
                    <span
                      key={i}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 20,
                        background: "#1a1a1a",
                        border: "1px solid #2a2a2a",
                        fontSize: 13,
                        color: "#ddd",
                      }}
                    >
                      {skill.name}
                    </span>
                  ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}