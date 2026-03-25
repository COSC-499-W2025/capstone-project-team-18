import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  getLatestResumeId,
  type ProjectListItem,
  type ResumeListItem,
  type ResumeListResponse,
} from "../api/apiClient";
import UploadProjectModal from "../components/update/modal/UploadProjectModal";

type PortfolioListItem = {
  id: number;
  title: string;
  creation_time?: string;
};

type ListPortfoliosResponse = {
  portfolios: PortfolioListItem[];
};

function formatDate(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function HomePage() {
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
  
  const [hoveredProjectName, setHoveredProjectName] = useState<string | null>(null);

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
    loadProjects();
    loadPortfolios();
    loadResumes();
    loadLatestResume();
  }, []);

  function loadLatestResume() {
  const resumeId = getLatestResumeId();
  setLatestResumeId(resumeId);
}

  async function handleUploadSuccess() {
  setShowUploadModal(false);
  await loadProjects();
}

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

    window.location.href = `/resume/${generated.id}`;
  } catch (e: any) {
    setError(e?.message ?? "Failed to create resume.");
  }
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
                    to={`/projects/${encodeURIComponent(
                      project.project_name
                    )}`}
                    onMouseEnter={() => setHoveredProjectName(project.project_name)}
                    onMouseLeave={() => setHoveredProjectName(null)}
                    style={{
                      display: "block",
                      textDecoration: "none",
                      color: "inherit",
                      border: "1px solid #2a2a2a",
                      borderRadius: 12,
                      padding: 14,
                      background:
                        hoveredProjectName === project.project_name
                          ? "#151515"
                          : "#101010",
                      transition: "background 0.2s ease, transform 0.2s ease",
                      transform:
                        hoveredProjectName === project.project_name
                          ? "translateY(-1px)"
                          : "translateY(0)",
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#ddd" }}>
                      {project.project_name}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: "#999",
                        marginTop: 6,
                      }}
                    >
                      Created: {formatDate(project.created_at)}
                    </div>
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
          {/* Resumes */}
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
                <h2 style={{ marginTop: 0 }}>Resumes</h2>

                  {resumesLoading && <div>Loading resumes…</div>}
                  {!resumesLoading && resumesError && (
                    <div style={{ color: "#ff8a8a", fontSize: 14 }}>
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
                            style={{
                              display: "block",
                              textDecoration: "none",
                              color: "inherit",
                              border: "1px solid #2a2a2a",
                              borderRadius: 12,
                              padding: 14,
                              background: "#101010",
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
                          <Link to="/resumes" style={{ color: "#6f7cff" }}>
                          View all
                          </Link>
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
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{p.title}</div>
                    <div style={{ fontSize: 12, color: "#999", marginTop: 6 }}>
                      Created: {formatDate(p.creation_time)}
                    </div>
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
