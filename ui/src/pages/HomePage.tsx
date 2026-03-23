import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  getLatestResumeId,
  type ProjectListItem,
  type ResumeResponse,
} from "../api/apiClient";
import UploadProjectModal from "../components/update/modal/UploadProjectModal";
import ProjectSkeleton from "@/components/ProjectSkeleton";

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
  const [latestResumeId, setLatestResumeId] = useState<number | null>(null);
  const [latestResume, setLatestResume] = useState<ResumeResponse | null>(null);
  const [hoveredProjectName, setHoveredProjectName] = useState<string | null>(null);

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

  useEffect(() => {
    loadProjects();
    loadPortfolios();
    loadLatestResume();
  }, []);

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
            
            {loading && projects.length === 0 ? (
              <>
              <div style={{ color: "#999", marginBottom: 12 }}>
                Loading projects...
                </div>
                <ProjectSkeleton count={3} />
                </>
                ) : (
                <>
                {isProjectAnalysisInProgress && (
                  <div style={{ color: "#999", marginBottom: 12 }}>
                    Project analysis in progress...
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
                            <div style={{ fontWeight: 600, color: "#ddd" }}>{project.project_name}
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
                          {isProjectAnalysisInProgress && <ProjectSkeleton count={3} />}
                          </div>
                        )}
                        </>
                      )}
                </div>

          <div style={{ marginTop: 20 }}>
            <Link to="/projects" style={{ color: "#6f7cff" }}>
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
