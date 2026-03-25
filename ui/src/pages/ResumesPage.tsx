import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  api,
  type ListProjectsResponse,
  type ProjectListItem,
  type ResumeListItem,
  type ResumeListResponse,
  type UserConfigResponse,
} from "../api/apiClient";

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function ResumesPage() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const [resumes, setResumes] = useState<ResumeListItem[]>([]);

  async function load() {
    try {
      setLoading(true);
      setError(null);

      const res = (await api.getResumes()) as ResumeListResponse;
      setResumes(Array.isArray(res?.resumes) ? res.resumes : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load resumes");
      setResumes([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreateResume() {
    try {
      setCreating(true);
      setCreateError(null);
      setError(null);

      const projectsResponse = (await api.getProjects()) as ListProjectsResponse;
      const projectNames = Array.isArray(projectsResponse?.projects)
        ? projectsResponse.projects
            .map((project: ProjectListItem) => project.project_name)
            .filter(Boolean)
        : [];

      if (projectNames.length === 0) {
        throw new Error("No uploaded projects found. Upload and mine a project first.");
      }

      let userConfigId: number | null = null;
      try {
        const userConfig = (await api.getUserConfig()) as UserConfigResponse;
        userConfigId = userConfig?.id ?? null;
      } catch {
        userConfigId = null;
      }

      const generatedResume = await api.generateResume({
        project_names: projectNames,
        user_config_id: userConfigId,
      });

      if (!generatedResume?.id) {
        throw new Error("Resume was created but no id was returned.");
      }

      navigate(`/resume/${generatedResume.id}`);
    } catch (e: any) {
      setCreateError(e?.message ?? "Failed to create resume.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>Resumes</h1>
          <p style={{ marginTop: 8, color: "#666" }}>
            Create and manage different resume versions.
          </p>
        </div>

        <button
          onClick={handleCreateResume}
          disabled={creating}
          style={{ padding: "10px 14px" }}
        >
          {creating ? "Creating..." : "Create Resume"}
        </button>
      </div>

      {createError && (
        <div
          style={{
            border: "1px solid #3a1f1f",
            borderRadius: 16,
            padding: 20,
            background: "#1a1111",
            color: "#ff8a8a",
            marginBottom: 16,
          }}
        >
          <strong>Error:</strong> {createError}
        </div>
      )}

      {loading && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
          }}
        >
          Loading resumes...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            border: "1px solid #3a1f1f",
            borderRadius: 16,
            padding: 20,
            background: "#1a1111",
            color: "#ff8a8a",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && resumes.length === 0 && (
        <div
          style={{
            border: "1px solid #2a2a2a",
            borderRadius: 16,
            padding: 20,
            background: "#161616",
            color: "#999",
          }}
        >
          No resumes yet. Click "Create Resume" to get started.
        </div>
      )}

      {!loading && !error && resumes.length > 0 && (
        <div style={{ display: "grid", gap: 16 }}>
          {resumes.map((resume) => (
            <Link
              key={resume.id}
              to={`/resume/${resume.id}`}
              style={{
                display: "block",
                textDecoration: "none",
                color: "inherit",
                border: "1px solid #2a2a2a",
                borderRadius: 16,
                padding: 18,
                background: "#161616",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 20 }}>
                    Resume #{resume.id}
                  </div>

                  <div style={{ fontSize: 13, color: "#999", marginTop: 8 }}>
                    Email: {resume.email || "—"}
                  </div>

                  <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                    GitHub: {resume.github || "—"}
                  </div>

                  <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                    Items: {resume.item_count}
                  </div>

                  <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                    Created: {formatDate(resume.created_at)}
                  </div>

                  <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
                    Updated: {formatDate(resume.last_updated)}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}