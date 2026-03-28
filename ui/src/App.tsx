import { useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { getLatestResumeId } from "./api/apiClient";
import SettingsModal from "./components/update/Modal/SettingsModal";
import HomePage from "./pages/HomePage";
import JobReadinessPage from "./pages/JobReadinessPage";
import PortfolioEditPage from "./pages/PortfolioEditPage";
import PortfoliosPage from "./pages/PortfoliosPage";
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
    color: isActive ? "#fff" : "#ccc",
    background: isActive ? "rgba(255, 255, 255, 0.12)" : "transparent",
    transition: "all 0.2s ease",
    display: "inline-block",
  };
}

export default function App() {
  const [showSettingsModal, setShowSettingsModal] = useState(false);

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
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 24px",
          borderBottom: "1px solid #eee",
        }}
      >
        <div style={{ fontWeight: 700 }}>Digital Artifact Miner</div>

        <nav style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
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

          <button
            onClick={() => setShowSettingsModal(true)}
            style={{
              padding: "8px 14px",
              borderRadius: 12,
              border: "none",
              background: "transparent",
              color: "#ccc",
              cursor: "pointer",
            }}
          >
            Settings
          </button>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<HomePage />} />
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
      </Routes>

      <SettingsModal open={showSettingsModal} onClose={() => setShowSettingsModal(false)} />
    </div>
  );
}
