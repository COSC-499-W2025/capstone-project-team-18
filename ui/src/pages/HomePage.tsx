import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  api,
  getLatestResumeId,
  type ProjectListItem,
  type ResumeListItem,
  type ResumeListResponse,
} from "../api/apiClient";
import UploadProjectModal from "../components/update/Modal/UploadProjectModal";
import ProjectSkeleton from "@/components/ProjectSkeleton";

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

export default function HomePage({ backendReady }: { backendReady: boolean }) {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const [portfolios, setPortfolios] = useState<PortfolioListItem[]>([]);
  const [portfoliosLoading, setPortfoliosLoading] = useState(true);
  const [portfoliosError, setPortfoliosError] = useState<string | null>(null);

  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [resumesLoading, setResumesLoading] = useState(true);
  const [resumesError, setResumesError] = useState<string | null>(null);
  const [latestResumeId, setLatestResumeId] = useState<number | null>(null);

  const [isProjectAnalysisInProgress, setIsProjectAnalysisInProgress] = useState(false);
  const [projectCountBeforeUpload, setProjectCountBeforeUpload] = useState(0);

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

  async function loadResumes() {
  try {
    setResumesLoading(true);
    setResumesError(null);

    const res = (await api.getResumes()) as ResumeListResponse;
    setResumes(Array.isArray(res?.resumes) ? res.resumes : []);
  } catch (e: any) {
    setResumesError(e?.message ?? "Failed to load resumes");
    setResumes([]);
  } finally {
    setResumesLoading(false);
  }
}

  useEffect(() => {
    if (!backendReady) return;
    loadProjects();
    loadPortfolios();
    loadResumes();
    loadLatestResume();
  }, [backendReady]);

  useEffect(() => {
    if ((location.state as any)?.openUploadModal) {
      setShowUploadModal(true);
    }
  }, [location.state]);

  function loadLatestResume() {
  const resumeId = getLatestResumeId();
  setLatestResumeId(resumeId);
}

  useEffect(() => {
  if (!isProjectAnalysisInProgress) return;

  const interval = setInterval(async () => {
    try {
      const res = await api.getProjects();
      const updatedProjects = Array.isArray(res?.projects) ? res.projects : [];

      setProjects(updatedProjects);
      setError(null);
      setLoading(false);

      if (updatedProjects.length > projectCountBeforeUpload) {
        setIsProjectAnalysisInProgress(false);
      }
    } catch (e: any) {
      setError(e?.message ?? "Failed to load projects");
      setIsProjectAnalysisInProgress(false);
    }
  }, 3000);

  return () => clearInterval(interval);
}, [isProjectAnalysisInProgress, projectCountBeforeUpload]);

async function handleCreateResume() {
  try {
    setError(null);

    const res = await api.getProjects();
    const projectNames = Array.isArray(res?.projects)
      ? res.projects.map((p) => p.project_name).filter(Boolean)
      : [];

    if (projectNames.length === 0) {
      throw new Error("No projects available to generate a resume.");
    }

    const generated = await api.generateResume({
      project_names: projectNames,
      user_config_id: null,
    });

    if (!generated?.id) {
      throw new Error("Resume created but no id returned.");
    }

    setLatestResumeId(generated.id);
    window.location.href = `/resume/${generated.id}`;
  } catch (e: any) {
    setError(e?.message ?? "Failed to create resume.");
  }
}

async function handleUploadSuccess() {
  setProjectCountBeforeUpload(projects.length);
  setShowUploadModal(false);
  setIsProjectAnalysisInProgress(true);
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
            View projects, resumes, and portfolios.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          style={{
            padding: "10px 18px",
            borderRadius: 10,
            border: "none",
            background: "var(--accent)",
            color: "#fff",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
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
            border: "1px solid var(--border)",
            borderRadius: 16,
            padding: 20,
            background: "var(--bg-surface)",
            minHeight: 220,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h2 style={{ marginTop: 0 }}>Projects</h2>

            {loading && projects.length === 0 ? (
              <>
                <div style={{ color: "#999", marginBottom: 12 }}>
                  Loading Projects...
                </div>
                <ProjectSkeleton count={3} />
              </>
            ) : (
              <>
                {isProjectAnalysisInProgress && (
                  <div style={{ color: "#999", marginBottom: 12 }}>
                    Project Analysis in Progress...
                  </div>
                )}
                {!error && projects.length === 0 && !isProjectAnalysisInProgress && (
                  <div>No projects found.</div>
                )}
                {!error && (
                  <div style={{ display: "grid", gap: 12 }}>
                    {projects.map((project) => (
                      <Link
                        key={project.project_name}
                        to={`/projects/${encodeURIComponent(project.project_name)}`}
                        state={{ from: "/" }}
                        onMouseEnter={(e) => {
                          const el = e.currentTarget as HTMLElement;
                          el.style.borderColor = "var(--hover-border)";
                          el.style.background = "var(--hover-bg)";
                          el.style.transform = "translateY(-1px)";
                        }}
                        onMouseLeave={(e) => {
                          const el = e.currentTarget as HTMLElement;
                          el.style.borderColor = "var(--border)";
                          el.style.background = "var(--bg-surface-deep)";
                          el.style.transform = "translateY(0)";
                        }}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          textDecoration: "none",
                          color: "inherit",
                          border: "1px solid var(--border)",
                          borderRadius: 12,
                          padding: 14,
                          background: "var(--bg-surface-deep)",
                          gap: 12,
                          transition: "background 0.2s ease, transform 0.2s ease, border-color 0.15s ease",
                          transform: "translateY(0)",
                        }}
                      >
                        <div style={{ fontWeight: 600, color: "#333", flex: 1, wordBreak: "break-word" }}>
                          {project.project_name}
                        </div>
                        {project.image_data && (
                          <div style={{ width: 64, height: 44, flexShrink: 0, borderRadius: 6, overflow: "hidden", background: "#f0f0f0" }}>
                            <img
                              src={getImageSrc(project.image_data)}
                              alt=""
                              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                            />
                          </div>
                        )}
                      </Link>
                    ))}
                    {isProjectAnalysisInProgress && <ProjectSkeleton count={3} />}
                  </div>
                )}
              </>
            )}
          </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/projects" style={{ color: "var(--accent)" }}>
              View All
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
          {/* Resumes */}
          <section
          style={{
            border: "1px solid var(--border)",
            borderRadius: 16,
            padding: 20,
            background: "var(--bg-surface)",
            minHeight: 220,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            }}
            >
              <div>
                <h2 style={{ marginTop: 0 }}>Resumes</h2>

                  {resumesLoading && <div>Loading resumes…</div>}
                  {!resumesLoading && resumesError && (
                    <div style={{ color: "var(--danger-text)", fontSize: 14 }}>
                      Failed to load resumes.
                      </div>
                    )}

                    {!resumesLoading && !resumesError && resumes.length === 0 && (
                      <div style={{ color: "#999" }}>No resumes yet.</div>
                      )}

                      {!resumesLoading && !resumesError && resumes.length > 0 && (
                        <div style={{ display: "grid", gap: 12 }}>
                          {resumes.slice(0, 3).map((resume) => (
                            <Link
                            key={resume.id}
                            to={`/resume/${resume.id}`}
                            state={{ from: "/" }}
                            onMouseEnter={(e) => {
                              const el = e.currentTarget as HTMLElement;
                              el.style.borderColor = "var(--hover-border)";
                              el.style.background = "var(--hover-bg)";
                            }}
                            onMouseLeave={(e) => {
                              const el = e.currentTarget as HTMLElement;
                              el.style.borderColor = "var(--border)";
                              el.style.background = "var(--bg-surface-deep)";
                            }}
                            style={{
                              display: "block",
                              textDecoration: "none",
                              color: "inherit",
                              border: "1px solid var(--border)",
                              borderRadius: 12,
                              padding: 14,
                              background: "var(--bg-surface-deep)",
                              transition: "border-color 0.15s ease, background 0.15s ease",
                            }}
                            >
                              <div style={{ fontWeight: 600 }}>
                                {resume.title || `Resume #${resume.id}`}
                                </div>
                                </Link>
                              ))}
                              </div>
                            )}
                        </div>

                        <div
                        style={{
                          marginTop: 20,
                          display: "flex",
                          gap: 12,
                          flexWrap: "wrap",
                        }}
                        >
                          <Link to="/resumes" style={{ color: "var(--accent)" }}>
                          View all
                          </Link>
                          </div>
          </section>

        {/* Portfolios */}
        <section
          style={{
            border: "1px solid var(--border)",
            borderRadius: 16,
            padding: 20,
            background: "var(--bg-surface)",
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
              <div style={{ color: "var(--danger-text)", fontSize: 14 }}>
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
                    state={{ from: "/" }}
                    style={{
                      display: "block",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid var(--border)",
                      borderRadius: 12,
                      padding: 14,
                      background: "var(--bg-surface-deep)",
                      transition: "border-color 0.15s, background 0.15s",
                    }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = "var(--hover-border)";
                      (e.currentTarget as HTMLElement).style.background = "var(--hover-bg)";
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                      (e.currentTarget as HTMLElement).style.background = "var(--bg-surface-deep)";
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{p.title}</div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/portfolios" style={{ color: "var(--accent)" }}>
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
