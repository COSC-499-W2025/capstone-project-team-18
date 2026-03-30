import { type CSSProperties, useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { api, getLatestResumeId } from "./api/apiClient";
import HomePage from "./pages/HomePage";
import JobReadinessPage from "./pages/JobReadinessPage";
import PortfolioEditPage from "./pages/PortfolioEditPage";
import PortfoliosPage from "./pages/PortfoliosPage";
import ProfilePage from "@/pages/ProfilePage";
import ProjectDetailsPage from "./pages/ProjectDetailsPage";
import ProjectsPage from "./pages/ProjectsPage";
import ResumePage from "./pages/ResumePage";
import ResumesPage from "./pages/ResumesPage";
import SkillsPage from "./pages/SkillsPage";
function ResumeRedirect() {
  const latestResumeId = getLatestResumeId();

  if (latestResumeId) {
    return <Navigate to={`/resume/${latestResumeId}`} replace />;
  }

  return <Navigate to="/resume/new" replace />;
}

function navLinkStyle(isActive: boolean) {
  return {
    padding: "8px 14px",
    borderRadius: 12,
    textDecoration: "none",
    color: isActive ? "#002145" : "var(--text-muted)",
    background: isActive ? "#e6eaf0" : "transparent",
    transition: "all 0.2s ease",
    display: "inline-block",
    fontWeight: isActive ? 600 : 400,
  };
}

export default function App() {
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    api.ping().then((ok) => setBackendDown(!ok));
  }, []);

  const location = useLocation();
  const isResumeRoute =
    location.pathname === "/resumes" ||
    location.pathname === "/resume" ||
    location.pathname.startsWith("/resume/");

  const isProjectsRoute =
    location.pathname === "/projects" ||
    location.pathname.startsWith("/projects/");

  const isJobReadinessRoute = location.pathname === "/job-readiness";

  return (
    <div style={{ fontFamily: "system-ui" }}>
      {backendDown && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              backgroundColor: "var(--danger-bg)",
              border: "1.5px solid var(--danger-text)",
              borderRadius: 12,
              padding: "32px 40px",
              textAlign: "center",
              maxWidth: 400,
            }}
          >
            <div style={{ fontSize: 28, marginBottom: 12 }}>⚠️</div>
            <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "var(--danger-text)" }}>
              Backend Unreachable
            </div>
            <div style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14 }}>
              Cannot connect to the API server. Please ensure the backend is running and try again.
            </div>
            <button
              onClick={() => api.ping().then((ok) => setBackendDown(!ok))}
              style={{
                padding: "8px 24px",
                borderRadius: 8,
                border: "none",
                backgroundColor: "#002145",
                color: "#fff",
                fontWeight: 600,
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              Refresh
            </button>
          </div>
        </div>
      )}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 100,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 24px 8px 120px",
          borderBottom: "1px solid var(--border)",
          backgroundColor: "var(--bg-surface)",
          WebkitAppRegion: "drag",
        } as CSSProperties}
      >
        <NavLink
          to="/"
          style={{
            fontWeight: 700,
            color: "var(--accent)",
            textDecoration: "none",
            WebkitAppRegion: "no-drag",
            fontSize: 20,
          } as CSSProperties}
        >
          Digital Artifact Miner
        </NavLink>

        <nav style={{ display: "flex", gap: 8, WebkitAppRegion: "no-drag" } as CSSProperties}>
          <NavLink to="/" end style={({ isActive }) => navLinkStyle(isActive)}>
            Dashboard
          </NavLink>

          <NavLink to="/projects" style={() => navLinkStyle(isProjectsRoute)}>
            Projects
          </NavLink>

          <NavLink to="/job-readiness" style={() => navLinkStyle(isJobReadinessRoute)}>
            Job Readiness
          </NavLink>

          <NavLink to="/portfolios" style={({ isActive }) => navLinkStyle(isActive)}>
            Portfolios
          </NavLink>

          <NavLink to="/skills" end style={({ isActive }) => navLinkStyle(isActive)}>
            Skills
          </NavLink>

          <NavLink to="/resumes" style={() => navLinkStyle(isResumeRoute)}>
            Resumes
          </NavLink>

          <NavLink to="/profile" style={({ isActive }) => navLinkStyle(isActive)}>
            Profile
          </NavLink>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<HomePage backendReady={!backendDown} />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectDetailsPage />} />
        <Route path="/job-readiness" element={<JobReadinessPage />} />
        <Route path="/skills" element={<SkillsPage />} />
        <Route path="/resumes" element={<ResumesPage />} />
        <Route path="/resume" element={<ResumeRedirect />} />
        <Route path="/resume/new" element={<ResumePage />} />
        <Route path="/resume/:id" element={<ResumePage />} />
        <Route path="/portfolios" element={<PortfoliosPage />} />
        <Route path="/portfolios/:id" element={<PortfolioEditPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </div>
  );
}
