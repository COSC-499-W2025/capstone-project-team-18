import { describe, it, expect, vi, afterEach } from "vitest";
import { api, getApiBaseUrl } from "./apiClient";

const fetchMock = vi.fn();
global.fetch = fetchMock as any;

describe("apiClient", () => {
  afterEach(() => {
    vi.clearAllMocks();
    delete process.env.VITE_API_BASE_URL;
  });

  it("formats base URL without trailing slash", () => {
    process.env.VITE_API_BASE_URL = "http://localhost:8000/";

    const base = getApiBaseUrl();
    expect(base).toBe("http://localhost:8000");
  });

  it("calls /projects with correct URL", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 1, name: "Test Project" }],
    });

    await api.getProjects();

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/projects");
  });

  it("calls /projects/:id with correct URL", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, name: "Test Project" }),
    });

    await api.getProject(1);

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/projects/1");
  });

  it("throws an error on non-200 response", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => "Internal Server Error",
    });

    await expect(api.getProjects()).rejects.toThrow("API request failed (500)");
  });
});

it("encodes project_name in /projects/:project_name URL", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ project_name: "My Project" }),
  });

  await api.getProject("My Project");

  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/projects/My%20Project"
  );
});

it("calls /projects/:project_name/insights with correct URL", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ project_name: "My Project", insights: [] }),
  });

  await api.getProjectInsights("My Project");

  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/projects/My%20Project/insights"
  );
});

it("ping calls /ping", async () => {
  fetchMock.mockResolvedValueOnce({ ok: true });

  const ok = await api.ping();

  expect(ok).toBe(true);
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/ping",
    expect.objectContaining({ signal: expect.any(AbortSignal) })
  );
});

it("includes status and URL in error message", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: false,
    status: 404,
    text: async () => "Not Found",
  });

  try {
    await api.getProject("missing");
    throw new Error("Expected getProject to throw");
  } catch (e: any) {
    expect(String(e.message)).toContain("API request failed (404)");
    expect(String(e.message)).toContain(
      "http://127.0.0.1:8000/projects/missing"
    );
  }
});

it("calls /resume/:id with correct URL", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ id: 1, items: [] }),
  });

  await api.getResume(1);

  expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/resume/1");
});

it("calls /resume/generate with correct URL and payload", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ id: 1, items: [] }),
  });

  await api.generateResume({
    project_names: ["Project A", "Project B"],
    user_config_id: 1,
  });

  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/resume/generate",
    expect.objectContaining({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_names: ["Project A", "Project B"],
        user_config_id: 1,
      }),
    })
  );
});

it("calls DELETE /projects/:project_name with correct URL and method", async () => {
  fetchMock.mockResolvedValueOnce({ ok: true, status: 204, text: async () => "" });

  await api.deleteProject("My Project");

  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/projects/My%20Project",
    expect.objectContaining({ method: "DELETE" })
  );
});

it("encodes spaces in project name for deleteProject", async () => {
  fetchMock.mockResolvedValueOnce({ ok: true, status: 204, text: async () => "" });

  await api.deleteProject("Hello World");

  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/projects/Hello%20World",
    expect.objectContaining({ method: "DELETE" })
  );
});

it("throws on deleteProject non-ok response", async () => {
  // deleteJson uses `msg || "API request failed (status)"`.
  // Empty body → msg is "", so the fallback message is used.
  fetchMock.mockResolvedValueOnce({
    ok: false,
    status: 404,
    text: async () => "",
  });

  await expect(api.deleteProject("ghost")).rejects.toThrow("API request failed (404)");
});

it("calls /job-readiness/analyze with correct URL and payload", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      fit_score: 84,
      summary: "Strong match",
      strengths: [],
      weaknesses: [],
      suggestions: [],
    }),
  });

  await api.analyzeJobReadiness({
    job_description: "Backend engineer role",
    resume_id: 7,
    project_names: ["Artifact Miner"],
  });

  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/job-readiness/analyze",
    expect.objectContaining({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_description: "Backend engineer role",
        resume_id: 7,
        project_names: ["Artifact Miner"],
      }),
    })
  );
});
