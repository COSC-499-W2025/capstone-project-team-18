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