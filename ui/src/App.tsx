import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailsPage from "./pages/ProjectDetailsPage";
import ResumePage from "./pages/ResumePage";
import ResumesPage from "./pages/ResumesPage";
import PortfoliosPage from "./pages/PortfoliosPage";
import PortfolioEditPage from "./pages/PortfolioEditPage";
import SkillsPage from "./pages/SkillsPage";
import { useEffect } from "react";
import ProfilePage from "@/pages/ProfilePage";
import { getLatestResumeId, api } from "./api/apiClient";

function ResumeRedirect() {
  const latestResumeId = getLatestResumeId();

  if (latestResumeId) {
    return <Navigate to={`/resume/${latestResumeId}`} replace />;
  }

  return <Navigate to="/resume/new" replace />;
}

export default function App() {
  const [showSettingsModal, setShowSettingsModal] = useState(false);
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

  return (
    <div style={{ fontFamily: "system-ui" }}>
      {backendDown && (
        <div style={{
          position: "fixed",
          inset: 0,
          backgroundColor: "rgba(0,0,0,0.75)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: "#1a0a0a",
            border: "1.5px solid #dc2626",
            borderRadius: 12,
            padding: "32px 40px",
            textAlign: "center",
            maxWidth: 400,
          }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>⚠️</div>
            <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "#f87171" }}>Backend Unreachable</div>
            <div style={{ color: "#fca5a5", marginBottom: 24, fontSize: 14 }}>
              Cannot connect to the API server. Please ensure the backend is running and try again.
            </div>
            <button
              onClick={() => api.ping().then((ok) => setBackendDown(!ok))}
              style={{
                padding: "8px 24px",
                borderRadius: 8,
                border: "none",
                backgroundColor: "#dc2626",
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
          padding: "8px 24px 8px 80px",
          borderBottom: "1px solid #eee",
          backgroundColor: "#242424",
          WebkitAppRegion: "drag",
        } as React.CSSProperties}
      >
        <NavLink to="/" style={{ fontWeight: 700, color: "inherit", textDecoration: "none", WebkitAppRegion: "no-drag" } as React.CSSProperties}>
          Digital Artifact Miner
        </NavLink>

        <nav style={{ display: "flex", gap: 8, WebkitAppRegion: "no-drag" } as React.CSSProperties}>
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
  style={() => ({
    padding: "8px 14px",
    borderRadius: 12,
    textDecoration: "none",
    color: isProjectsRoute ? "#fff" : "#ccc",
    background: isProjectsRoute
      ? "rgba(255, 255, 255, 0.12)"
      : "transparent",
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
            style={() => ({
              padding: "8px 14px",
              borderRadius: 12,
              textDecoration: "none",
              color: isResumeRoute ? "#fff" : "#ccc",
              background: isResumeRoute ? "rgba(255, 255, 255, 0.12)" : "transparent",
              transition: "all 0.2s ease",
              display: "inline-block",
            })}
          >
            Resumes
          </NavLink>

          <NavLink
            to="/profile"
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
            Profile
          </NavLink>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<HomePage backendReady={!backendDown} />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectDetailsPage />} />
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