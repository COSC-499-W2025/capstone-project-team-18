import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailsPage from "./pages/ProjectDetailsPage";
import SkillsPage from "./pages/SkillsPage";
import ResumePage from "./pages/ResumePage";
import ResumesPage from "./pages/ResumesPage";
import PortfoliosPage from "./pages/PortfoliosPage";
import PortfolioEditPage from "./pages/PortfolioEditPage";
import { useState } from "react";
import SettingsModal from "./components/update/modal/SettingsModal";
import { getLatestResumeId } from "./api/apiClient";

function ResumeRedirect() {
  const latestResumeId = getLatestResumeId();

  if (latestResumeId) {
    return <Navigate to={`/resume/${latestResumeId}`} replace />;
  }

  return <Navigate to="/resume/new" replace />;
}

export default function App() {
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  return (
    <div style={{ fontFamily: "system-ui" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 24px",
          borderBottom: "1px solid #eee"
        }}
      >
        <div style={{ fontWeight: 700 }}>Digital Artifact Miner</div>

        <nav style={{ display: "flex", gap: 8 }}>
          <NavLink
          to="/"
          end
          style={({ isActive }) => ({
            padding: "8px 14px",
            borderRadius: 12,
            textDecoration: "none",
            color: isActive ? "#fff" : "#ccc",
            background: isActive ? "rgba(255, 255, 255, 0.12)" : "transparent",
            transition: "all 0.2s ease",
            display: "inline-block",
            })}
            >
              Dashboard
              </NavLink>

          <NavLink
          to="/projects"
          end
          style={({ isActive }) => ({
            padding: "8px 14px",
            borderRadius: 12,
            textDecoration: "none",
            color: isActive ? "#fff" : "#ccc",
            background: isActive ? "rgba(255, 255, 255, 0.12)" : "transparent",
            transition: "all 0.2s ease",
            display: "inline-block",
            })}
            >
              Projects
              </NavLink>

          <NavLink
          to="/portfolios"
          style={({ isActive }) => ({
            padding: "8px 14px",
            borderRadius: 12,
            textDecoration: "none",
            color: isActive ? "#fff" : "#ccc",
            background: isActive ? "rgba(255, 255, 255, 0.12)" : "transparent",
            transition: "all 0.2s ease",
            display: "inline-block",
            })}
            >
              Portfolios
          </NavLink>

          <NavLink
          to="/skills"
          end
          style={({ isActive }) => ({
            padding: "8px 14px",
            borderRadius: 12,
            textDecoration: "none",
            color: isActive ? "#fff" : "#ccc",
            background: isActive ? "rgba(255, 255, 255, 0.12)" : "transparent",
            transition: "all 0.2s ease",
            display: "inline-block",
            })}
            >
              Skills
          </NavLink>

          <NavLink
          to="/resumes"
          style={({ isActive }) => ({
            padding: "8px 14px",
            borderRadius: 12,
            textDecoration: "none",
            color: isActive ? "#fff" : "#ccc",
            background: isActive ? "rgba(255, 255, 255, 0.12)" : "transparent",
            transition: "all 0.2s ease",
            display: "inline-block",
            })}
            >
              Resume
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
        <Route path="/skills" element={<SkillsPage />} />
        <Route path="/resumes" element={<ResumesPage />} />
        <Route path="/resume" element={<ResumeRedirect />} />
        <Route path="/resume/new" element={<ResumePage />} />
        <Route path="/resume/:id" element={<ResumePage />} />
        <Route path="/portfolios" element={<PortfoliosPage />} />
        <Route path="/portfolios/:id" element={<PortfolioEditPage />} />
      </Routes>

      <SettingsModal
      open={showSettingsModal}
      onClose={() => setShowSettingsModal(false)}
      />
    </div>
  );
}