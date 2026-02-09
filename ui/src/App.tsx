import type { CSSProperties } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailsPage from "./pages/ProjectDetailsPage";
import SkillsPage from "./pages/SkillsPage";

const linkStyle: CSSProperties = {
  padding: "6px 10px",
  borderRadius: 8,
  textDecoration: "none",
  color: "inherit"
};

export default function App() {
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
              Home
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
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectDetailsPage />} />
        <Route path="/skills" element={<SkillsPage />} />
      </Routes>
    </div>
  );
}