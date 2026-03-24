import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  getLatestResumeId,
  type ProjectListItem,
  type ResumeResponse,
} from "../api/apiClient";
import UploadProjectModal from "../components/update/modal/UploadProjectModal";

type PortfolioListItem = {
  id: number;
  title: string;
};

type ListPortfoliosResponse = {
  portfolios: PortfolioListItem[];
};

function getImageSrc(base64: string): string {
  if (base64.startsWith("/9j/")) return `data:image/jpeg;base64,${base64}`;
  if (base64.startsWith("iVBOR")) return `data:image/png;base64,${base64}`;
  if (base64.startsWith("R0lG")) return `data:image/gif;base64,${base64}`;
  if (base64.startsWith("UklG")) return `data:image/webp;base64,${base64}`;
  return `data:image/jpeg;base64,${base64}`;
}

export default function HomePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const [portfolios, setPortfolios] = useState<PortfolioListItem[]>([]);
  const [portfoliosLoading, setPortfoliosLoading] = useState(true);
  const [portfoliosError, setPortfoliosError] = useState<string | null>(null);
  const [latestResumeId, setLatestResumeId] = useState<number | null>(null);
  const [latestResume, setLatestResume] = useState<ResumeResponse | null>(null);
  async function loadProjects() {
    try {
      setLoading(true);
      setError(null);

      const res = await api.getProjects();
      setProjects(Array.isArray(res?.projects) ? res.projects : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load projects");
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadPortfolios() {
    try {
      setPortfoliosLoading(true);
      setPortfoliosError(null);
      const res = (await api.getPortfolios()) as ListPortfoliosResponse;
      setPortfolios(Array.isArray(res?.portfolios) ? res.portfolios : []);
    } catch (e: any) {
      setPortfoliosError(e?.message ?? "Failed to load portfolios");
      setPortfolios([]);
    } finally {
      setPortfoliosLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
    loadPortfolios();
    loadLatestResume();
  }, []);

  async function loadLatestResume() {
    const resumeId = getLatestResumeId();
    setLatestResumeId(resumeId);

    if (!resumeId) {
      setLatestResume(null);
      return;
    }

    try {
      const resume = await api.getResume(resumeId);
      setLatestResume(resume);
    } catch {
      setLatestResume(null);
    }
  }

  async function handleUploadSuccess() {
    setShowUploadModal(false);
    await loadProjects();
  }

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>Dashboard</h1>
          <p style={{ marginTop: 8, color: "#666" }}>
            Manage projects, resumes, portfolios, and settings.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          style={{ padding: "10px 14px" }}
        >
          Upload Project
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ marginBottom: 16, color: "crimson" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.15fr 0.85fr",
          gap: 20,
          alignItems: "stretch",
        }}
      >
        {/* Projects */}
        <section
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
            minHeight: 220,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h2 style={{ marginTop: 0 }}>Projects</h2>

            {loading && <div>Loading projects…</div>}

            {!loading && !error && projects.length === 0 && (
              <div>No projects found.</div>
            )}

            {!loading && !error && projects.length > 0 && (
              <div style={{ display: "grid", gap: 12 }}>
                {projects.map((project) => (
                  <Link
                    key={project.project_name}
                    to={`/projects/${encodeURIComponent(project.project_name)}`}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid #2a2a2a",
                      borderRadius: 12,
                      padding: 14,
                      background: "#101010",
                      gap: 12,
                      transition: "border-color 0.15s, background 0.15s",
                    }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = "#6f7cff";
                      (e.currentTarget as HTMLElement).style.background = "#1a1a2e";
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = "#2a2a2a";
                      (e.currentTarget as HTMLElement).style.background = "#101010";
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#ddd", flex: 1, wordBreak: "break-word" }}>
                      {project.project_name}
                    </div>
                    {project.image_data && (
                      <div style={{ width: 64, height: 44, flexShrink: 0, borderRadius: 6, overflow: "hidden", background: "#0d0d0d" }}>
                        <img
                          src={getImageSrc(project.image_data)}
                          alt=""
                          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                        />
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/projects" style={{ color: "#6f7cff" }}>
              View all
            </Link>
          </div>
        </section>

        <div
          style={{
            display: "grid",
            gridTemplateRows: "1fr 1fr",
            gap: 20,
          }}
        >
          {/* Resume */}
          <section
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 16,
              padding: 20,
              background: "#161616",
              minHeight: 220,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <h2 style={{ marginTop: 0 }}>Resume</h2>
              <div style={{ color: "#999", lineHeight: 1.6, marginBottom: 16 }}>
                View generated resume content, review extracted skills, and
                review resume items.
              </div>

              {latestResume?.items && latestResume.items.length > 0 ? (
                <div style={{ display: "grid", gap: 10 }}>
                  {latestResume.items.map((item, index) => (
                    <div
                      key={`${item.title}-${index}`}
                      style={{
                        border: "1px solid #2a2a2a",
                        borderRadius: 10,
                        padding: "10px 12px",
                        background: "#101010",
                        color: "#ddd",
                      }}
                    >
                      {item.title}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "#999" }}>No generated resume items yet.</div>
              )}
            </div>

            <div style={{ marginTop: 20 }}>
              {latestResumeId ? (
                <Link
                  to={`/resume/${latestResumeId}`}
                  style={{ color: "#6f7cff" }}
                >
                  Open Resume
                </Link>
              ) : (
                <span style={{ color: "#999" }}>
                  Generate a resume to view it here.
                </span>
              )}
            </div>
          </section>

        {/* Portfolios */}
        <section
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
            minHeight: 220,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h2 style={{ marginTop: 0 }}>Portfolios</h2>

            {portfoliosLoading && <div>Loading portfolios…</div>}

            {!portfoliosLoading && portfoliosError && (
              <div style={{ color: "#ff8a8a", fontSize: 14 }}>
                Failed to load.
              </div>
            )}

            {!portfoliosLoading && !portfoliosError && portfolios.length === 0 && (
              <div style={{ color: "#999" }}>No portfolios yet.</div>
            )}

            {!portfoliosLoading && !portfoliosError && portfolios.length > 0 && (
              <div style={{ display: "grid", gap: 12 }}>
                {portfolios.slice(0, 3).map((p) => (
                  <Link
                    key={p.id}
                    to={`/portfolios/${p.id}`}
                    style={{
                      display: "block",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid #2a2a2a",
                      borderRadius: 12,
                      padding: 14,
                      background: "#101010",
                      transition: "border-color 0.15s, background 0.15s",
                    }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = "#6f7cff";
                      (e.currentTarget as HTMLElement).style.background = "#1a1a2e";
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = "#2a2a2a";
                      (e.currentTarget as HTMLElement).style.background = "#101010";
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{p.title}</div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/portfolios" style={{ color: "#6f7cff" }}>
              View all
            </Link>
          </div>
        </section>
        </div>
      </div>

      <UploadProjectModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}
