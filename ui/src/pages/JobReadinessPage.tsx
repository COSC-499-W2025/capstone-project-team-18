import { useEffect, useState } from "react";
import {
  api,
  getLatestResumeId,
  type JobReadinessResponse,
  type ProjectListItem,
  type ResumeListItem,
  type ResumeListResponse,
  type ListProjectsResponse,
} from "../api/apiClient";

function scoreTone(score: number) {
  if (score >= 80) return { label: "Strong fit", color: "#52c26d" };
  if (score >= 60) return { label: "Promising fit", color: "#f2b84b" };
  return { label: "Needs work", color: "var(--danger-text)" };
}

export default function JobReadinessPage() {
  const [loadingEvidence, setLoadingEvidence] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>("");
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [result, setResult] = useState<JobReadinessResponse | null>(null);

  useEffect(() => {
    async function loadEvidence() {
      try {
        setLoadingEvidence(true);
        setLoadError(null);

        const [resumeRes, projectRes] = await Promise.all([
          api.getResumes() as Promise<ResumeListResponse>,
          api.getProjects() as Promise<ListProjectsResponse>,
        ]);

        const nextResumes = Array.isArray(resumeRes?.resumes) ? resumeRes.resumes : [];
        const nextProjects = Array.isArray(projectRes?.projects) ? projectRes.projects : [];
        const latestResumeId = getLatestResumeId();
        const preferredResume =
          nextResumes.find((resume) => resume.id === latestResumeId) ?? nextResumes[0];

        setResumes(nextResumes);
        setProjects(nextProjects);
        setSelectedResumeId(preferredResume ? String(preferredResume.id) : "");
      } catch (error: any) {
        setLoadError(error?.message ?? "Failed to load evidence");
        setResumes([]);
        setProjects([]);
      } finally {
        setLoadingEvidence(false);
      }
    }

    loadEvidence();
  }, []);

  function toggleProject(projectName: string) {
    setSelectedProjects((current) =>
      current.includes(projectName)
        ? current.filter((name) => name !== projectName)
        : [...current, projectName]
    );
  }

  async function handleAnalyze() {
    try {
      setSubmitting(true);
      setSubmitError(null);

      const response = await api.analyzeJobReadiness({
        job_description: jobDescription,
        resume_id: selectedResumeId ? Number(selectedResumeId) : null,
        project_names: selectedProjects,
      });

      setResult(response);
    } catch (error: any) {
      const msg = error?.message ?? "";
      let displayError = msg || "Failed to analyze job readiness";
      try {
        const parsed = JSON.parse(msg);
        if (parsed?.error_code === "AI_SERVICE_UNAVAILABLE") {
          displayError = "AI analysis is unavailable because you have not consented to AI features. Please enable AI consent in your profile settings to use Job Readiness analysis.";
        }
      } catch {
        // not JSON, use message as-is
      }
      setSubmitError(displayError);
      setResult(null);
    } finally {
      setSubmitting(false);
    }
  }

  const selectedResume = resumes.find((resume) => String(resume.id) === selectedResumeId);
  const scoreInfo = result ? scoreTone(result.fit_score) : null;

  return (
    <div style={{ padding: 24, paddingTop: 40 }}>
      <div style={{ maxWidth: 1240, margin: "0 auto" }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ margin: 0, fontSize: 30 }}>Job Readiness</h1>
          <p style={{ margin: "10px 0 0", color: "var(--text-muted)", maxWidth: 760, lineHeight: 1.6 }}>
            Compare a target job description against your current resume and project evidence,
            then review strengths, gaps, and the highest-priority actions to improve your fit.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: 24,
            alignItems: "start",
          }}
        >
          <section
            style={{
              border: "1px solid var(--border)",
              borderRadius: 20,
              padding: 20,
              background: "var(--bg-surface)",
            }}
          >
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>Analysis Input</div>
              <div style={{ color: "var(--text-muted)", lineHeight: 1.5 }}>
                Pick the evidence you want the analyzer to use, then run the readiness assessment.
              </div>
            </div>

            {loadingEvidence && (
              <div
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 14,
                  padding: 16,
                  background: "var(--bg-surface-deep)",
                  color: "var(--text-muted)",
                }}
              >
                Loading resumes and projects...
              </div>
            )}

            {!loadingEvidence && loadError && (
              <div
                style={{
                  border: "1px solid var(--danger-bg-strong)",
                  borderRadius: 14,
                  padding: 16,
                  background: "var(--danger-bg)",
                  color: "var(--danger-text)",
                  marginBottom: 16,
                }}
              >
                <strong>Error:</strong> {loadError}
              </div>
            )}

            <div style={{ display: "grid", gap: 18 }}>
              <label style={{ display: "grid", gap: 8 }}>
                <span style={{ fontWeight: 600 }}>Job Description</span>
                <textarea
                  value={jobDescription}
                  onChange={(event) => setJobDescription(event.target.value)}
                  placeholder="Paste the job posting here"
                  rows={12}
                  style={{
                    width: "100%",
                    resize: "vertical",
                    borderRadius: 14,
                    border: "1px solid var(--border)",
                    background: "var(--bg-input)",
                    color: "var(--text-primary)",
                    padding: 14,
                    lineHeight: 1.5,
                    font: "inherit",
                    boxSizing: "border-box",
                  }}
                />
              </label>

              <label style={{ display: "grid", gap: 8 }}>
                <span style={{ fontWeight: 600 }}>Resume Evidence</span>
                <select
                  value={selectedResumeId}
                  onChange={(event) => setSelectedResumeId(event.target.value)}
                  style={{
                    borderRadius: 12,
                    border: "1px solid var(--border)",
                    background: "var(--bg-input)",
                    color: "var(--text-primary)",
                    padding: "12px 14px",
                    font: "inherit",
                  }}
                >
                  <option value="">No resume selected</option>
                  {resumes.map((resume) => (
                    <option key={resume.id} value={resume.id}>
                      {resume.title || `Resume #${resume.id}`}
                    </option>
                  ))}
                </select>
                <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
                  {selectedResume
                    ? `Selected: ${selectedResume.title || `Resume #${selectedResume.id}`}`
                    : "You can submit without a resume if project evidence is enough."}
                </div>
              </label>

              <div style={{ display: "grid", gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>Project Evidence</div>
                  <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
                    Select the projects that best demonstrate the skills needed for this role.
                  </div>
                </div>

                <div
                  style={{
                    border: "1px solid var(--border)",
                    borderRadius: 14,
                    background: "var(--bg-surface-deep)",
                    padding: 12,
                    maxHeight: 280,
                    overflowY: "auto",
                  }}
                >
                  {projects.length === 0 ? (
                    <div style={{ color: "var(--text-muted)", padding: 8 }}>No projects available.</div>
                  ) : (
                    <div style={{ display: "grid", gap: 10 }}>
                      {projects.map((project) => {
                        const checked = selectedProjects.includes(project.project_name);
                        return (
                          <label
                            key={project.project_name}
                            style={{
                              display: "flex",
                              alignItems: "flex-start",
                              gap: 10,
                              padding: 10,
                              borderRadius: 12,
                              background: checked ? "var(--hover-bg)" : "var(--bg-surface)",
                              border: checked ? "1px solid var(--hover-border)" : "1px solid var(--border)",
                              cursor: "pointer",
                              transition: "background 0.15s ease, border-color 0.15s ease",
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleProject(project.project_name)}
                              style={{ marginTop: 3 }}
                            />
                            <span style={{ lineHeight: 1.4 }}>{project.project_name}</span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                  flexWrap: "wrap",
                  color: "var(--text-muted)",
                  fontSize: 13,
                }}
              >
                <span>
                  {selectedResumeId ? "1 resume selected" : "No resume selected"} • {selectedProjects.length} project{selectedProjects.length === 1 ? "" : "s"} selected
                </span>
                <button
                  onClick={handleAnalyze}
                  disabled={submitting || loadingEvidence || !jobDescription.trim()}
                  style={{
                    padding: "10px 18px",
                    borderRadius: 10,
                    border: "none",
                    background: "var(--accent)",
                    color: "#fff",
                    fontWeight: 600,
                    cursor: submitting ? "progress" : "pointer",
                    opacity: submitting ? 0.7 : 1,
                  }}
                >
                  {submitting ? "Analyzing..." : "Analyze Readiness"}
                </button>
              </div>

              {submitError && (
                <div
                  style={{
                    border: "1px solid var(--danger-bg-strong)",
                    borderRadius: 14,
                    padding: 16,
                    background: "var(--danger-bg)",
                    color: "var(--danger-text)",
                    lineHeight: 1.5,
                  }}
                >
                  <strong>Analysis failed:</strong> {submitError}
                </div>
              )}
            </div>
          </section>

          <section
            style={{
              border: "1px solid var(--border)",
              borderRadius: 20,
              padding: 20,
              background: "var(--bg-surface)",
              minHeight: 520,
              maxHeight: "min(820px, calc(100vh - 140px))",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                paddingRight: 6,
              }}
            >
            {!result ? (
              <div
                style={{
                  height: "100%",
                  minHeight: 480,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  textAlign: "center",
                  color: "var(--text-muted)",
                  padding: 24,
                }}
              >
                Run an analysis to see your fit score, evidence-backed strengths, gaps, and prioritized next steps.
              </div>
            ) : (
              <div style={{ display: "grid", gap: 20 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-end",
                    gap: 16,
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <div style={{ color: "var(--text-muted)", marginBottom: 6 }}>Overall Fit</div>
                    <div style={{ fontSize: 52, fontWeight: 800, lineHeight: 1 }}>
                      {result.fit_score}
                      <span style={{ fontSize: 20, color: "var(--text-muted)", marginLeft: 6 }}>/100</span>
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "10px 14px",
                      borderRadius: 999,
                      border: `1px solid ${scoreInfo?.color}`,
                      color: scoreInfo?.color,
                      background: "rgba(255,255,255,0.02)",
                      fontWeight: 700,
                    }}
                  >
                    {scoreInfo?.label}
                  </div>
                </div>

                <div
                  style={{
                    border: "1px solid var(--border)",
                    borderRadius: 16,
                    padding: 18,
                    background: "var(--bg-surface)",
                    lineHeight: 1.6,
                    color: "var(--text-primary)",
                  }}
                >
                  {result.summary}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                    gap: 16,
                  }}
                >
                  <div style={{ border: "1px solid #bbf7d0", borderRadius: 16, padding: 16, background: "#f0faf8" }}>
                    <div style={{ fontWeight: 700, marginBottom: 12, color: "#166534" }}>Strengths</div>
                    <div style={{ display: "grid", gap: 12 }}>
                      {result.strengths.map((strength) => (
                        <article key={`${strength.rank}-${strength.item}`}>
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>
                            {strength.rank}. {strength.item}
                          </div>
                          <div style={{ color: "var(--text-muted)", lineHeight: 1.5 }}>{strength.reason}</div>
                        </article>
                      ))}
                    </div>
                  </div>

                  <div style={{ border: "1px solid #fde68a", borderRadius: 16, padding: 16, background: "#fffdf0" }}>
                    <div style={{ fontWeight: 700, marginBottom: 12, color: "#92400e" }}>Weaknesses</div>
                    <div style={{ display: "grid", gap: 12 }}>
                      {result.weaknesses.map((weakness) => (
                        <article key={`${weakness.rank}-${weakness.item}`}>
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>
                            {weakness.rank}. {weakness.item}
                          </div>
                          <div style={{ color: "var(--text-muted)", lineHeight: 1.5 }}>{weakness.reason}</div>
                        </article>
                      ))}
                    </div>
                  </div>
                </div>

                <div>
                  <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 12 }}>Recommended Next Steps</div>
                  <div style={{ display: "grid", gap: 14 }}>
                    {result.suggestions.map((suggestion) => (
                      <article
                        key={`${suggestion.priority}-${suggestion.item}`}
                        style={{
                          border: "1px solid var(--border)",
                          borderRadius: 18,
                          padding: 18,
                          background: "var(--bg-surface)",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            marginBottom: 12,
                            flexWrap: "wrap",
                          }}
                        >
                          <span
                            style={{
                              padding: "5px 10px",
                              borderRadius: 999,
                              background: "var(--hover-bg)",
                              color: "var(--accent)",
                              fontSize: 12,
                              fontWeight: 700,
                              letterSpacing: 0.3,
                              textTransform: "uppercase",
                            }}
                          >
                            Priority {suggestion.priority}
                          </span>
                          <span
                            style={{
                              padding: "5px 10px",
                              borderRadius: 999,
                              border: "1px solid var(--border)",
                              color: "var(--text-muted)",
                              fontSize: 12,
                              textTransform: "capitalize",
                            }}
                          >
                            {suggestion.resource_type || "Resource"}
                          </span>
                        </div>

                        <div style={{ fontWeight: 700, fontSize: 21, lineHeight: 1.35, marginBottom: 12 }}>
                          {suggestion.item}
                        </div>

                        <div style={{ color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: 18 }}>
                          {suggestion.reason}
                        </div>

                        <div style={{ display: "grid", gap: 14 }}>
                          <div>
                            <div style={{ color: "var(--text-muted)", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 6 }}>
                              Start with
                            </div>
                            <div style={{ color: "var(--text-secondary)", lineHeight: 1.5 }}>
                              {suggestion.resource_name || "Not specified"}
                            </div>
                          </div>

                          <div
                            style={{
                              border: "1px solid var(--border)",
                              borderRadius: 14,
                              padding: 14,
                              background: "var(--bg-surface-deep)",
                            }}
                          >
                            <div style={{ color: "var(--text-muted)", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 6 }}>
                              Suggested approach
                            </div>
                            <div style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
                              {suggestion.resource_hint || "Use this action to create stronger evidence for your resume, portfolio, or selected projects."}
                            </div>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              </div>
            )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
