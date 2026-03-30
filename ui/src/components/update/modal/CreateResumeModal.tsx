import { useEffect, useRef, useState } from "react";
import { api } from "../../../api/apiClient";

type ProjectListItem = {
  project_name: string;
};

type CreateResumeModalProps = {
  open: boolean;
  onClose: () => void;
  onCreated: (id: number) => void;
};

export default function CreateResumeModal({
  open,
  onClose,
  onCreated,
}: CreateResumeModalProps) {
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(
    new Set()
  );
  const [title, setTitle] = useState("");
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const loadedRef = useRef(false);

  async function loadProjects() {
    setProjectsLoading(true);
    setProjectsError(null);
    try {
      const res = await api.getProjects();
      setProjects(Array.isArray(res?.projects) ? res.projects : []);
    } catch (e: any) {
      setProjectsError(e?.message ?? "Failed to load projects");
      setProjects([]);
    } finally {
      setProjectsLoading(false);
    }
  }

  useEffect(() => {
    if (open && !loadedRef.current) {
      loadedRef.current = true;
      loadProjects();
    }
    if (!open) {
      loadedRef.current = false;
    }
  }, [open]);

  if (!open) return null;

  function resetState() {
    setSelectedProjects(new Set());
    setTitle("");
    setSubmitError(null);
  }

  function handleClose() {
    if (isSubmitting) return;
    resetState();
    onClose();
  }

  function toggleProject(name: string) {
    if (isSubmitting) return;
    setSelectedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }

  const canSubmit = selectedProjects.size > 0 && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit) return;
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      let userConfigId: number | null = null;
      try {
        const userConfig = await api.getUserConfig();
        userConfigId = userConfig?.id ?? null;
      } catch {
        userConfigId = null;
      }

      const res = await api.generateResume({
        project_names: [...selectedProjects],
        user_config_id: userConfigId,
        title: title.trim() || null,
      });

      const newId = res?.id;
      if (!newId) {
        throw new Error("Resume created but no ID returned.");
      }

      resetState();
      onCreated(newId);
    } catch (e: any) {
      setSubmitError(e?.message ?? "Failed to create resume.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      onClick={handleClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.68)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 560,
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: 18,
          padding: 24,
          boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h2 style={{ margin: 0 }}>Create Resume</h2>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            style={{
              border: "none",
              background: "transparent",
              color: isSubmitting ? "#777" : "#444",
              fontSize: 20,
              cursor: isSubmitting ? "not-allowed" : "pointer",
            }}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label
            style={{
              fontSize: 14,
              color: "var(--text-muted)",
              display: "block",
              marginBottom: 6,
            }}
          >
            Title <span style={{ color: "var(--text-muted)" }}>(optional)</span>
          </label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={isSubmitting}
            placeholder="e.g. Software Engineer Resume"
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "9px 12px",
              borderRadius: 10,
              border: "1px solid var(--border)",
              background: "var(--bg-input)",
              color: "var(--text-primary)",
              fontSize: 14,
              outline: "none",
              fontFamily: "inherit",
              opacity: isSubmitting ? 0.6 : 1,
            }}
          />
        </div>

        <div style={{ marginBottom: 20 }}>
          <label
            style={{
              fontSize: 14,
              color: "var(--text-muted)",
              display: "block",
              marginBottom: 6,
            }}
          >
            Select Projects *
          </label>

          {projectsLoading && (
            <div
              style={{
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 16,
                background: "var(--bg-surface)",
                color: "var(--text-muted)",
                fontSize: 14,
              }}
            >
              Loading projects...
            </div>
          )}

          {!projectsLoading && projectsError && (
            <div
              style={{
                border: "1px solid var(--danger-bg-strong)",
                borderRadius: 12,
                padding: 16,
                background: "var(--danger-bg)",
                color: "var(--danger-text)",
                fontSize: 14,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>{projectsError}</span>
              <button
                onClick={loadProjects}
                style={{
                  padding: "6px 10px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: "#333",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                Retry
              </button>
            </div>
          )}

          {!projectsLoading && !projectsError && projects.length === 0 && (
            <div
              style={{
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 16,
                background: "var(--bg-surface)",
                color: "var(--text-muted)",
                fontSize: 14,
              }}
            >
              No projects available. Upload a project first.
            </div>
          )}

          {!projectsLoading && !projectsError && projects.length > 0 && (
            <div
              style={{
                maxHeight: 240,
                overflowY: "auto",
                display: "grid",
                gap: 8,
                padding: 2,
              }}
            >
              {projects.map((p) => {
                const selected = selectedProjects.has(p.project_name);
                return (
                  <button
                    key={p.project_name}
                    onClick={() => toggleProject(p.project_name)}
                    disabled={isSubmitting}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: 12,
                      borderRadius: 10,
                      border: selected
                        ? "1px solid var(--btn-primary)"
                        : "1px solid var(--border)",
                      background: selected ? "var(--accent-subtle)" : "var(--bg-surface)",
                      color: selected ? "var(--text-primary)" : "var(--text-secondary)",
                      cursor: isSubmitting ? "not-allowed" : "pointer",
                      textAlign: "left",
                      fontSize: 14,
                      transition: "all 0.15s ease",
                      opacity: isSubmitting ? 0.6 : 1,
                    }}
                  >
                    <span
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: 4,
                        border: selected ? "2px solid var(--btn-primary)" : "2px solid var(--border-strong)",
                        background: selected ? "var(--btn-primary)" : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontSize: 11,
                        color: "#fff",
                      }}
                    >
                      {selected ? "✓" : ""}
                    </span>
                    {p.project_name}
                  </button>
                );
              })}
            </div>
          )}

          {selectedProjects.size > 0 && (
            <div style={{ fontSize: 12, color: "var(--accent)", marginTop: 8 }}>
              {selectedProjects.size} project
              {selectedProjects.size !== 1 ? "s" : ""} selected
            </div>
          )}
        </div>

        {submitError && (
          <div style={{ color: "var(--danger-text)", fontSize: 14, marginBottom: 12 }}>
            {submitError}
          </div>
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
            {isSubmitting
              ? "Creating resume... this may take a moment."
              : "Select at least one project."}
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleClose}
              disabled={isSubmitting}
              style={{
                padding: "10px 14px",
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: 10,
                color: isSubmitting ? "#777" : "#444",
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              Cancel
            </button>

            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                border: "none",
                background: canSubmit ? "var(--btn-primary)" : "var(--bg-surface-deep)",
                color: canSubmit ? "#fff" : "var(--text-muted)",
                fontWeight: 600,
                opacity: canSubmit ? 1 : 0.6,
                cursor: canSubmit ? "pointer" : "not-allowed",
              }}
            >
              {isSubmitting ? "Creating..." : "Create Resume"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
