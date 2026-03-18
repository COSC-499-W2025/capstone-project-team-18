const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim();
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

/**
 * Resolve API base URL.
 * Priority:
 * 1. VITE_API_BASE_URL (for dev / different environments)
 * 2. Default localhost FastAPI
 */

export function getApiBaseUrl(): string {
  const nodeEnvBase =
    typeof process !== "undefined" ? process.env.VITE_API_BASE_URL : undefined;

  const viteEnvBase =
    typeof import.meta !== "undefined"
      ? ((import.meta as any).env?.VITE_API_BASE_URL as string | undefined)
      : undefined;

  return normalizeBaseUrl(nodeEnvBase ?? viteEnvBase ?? DEFAULT_BASE_URL);
}

async function getJson<T>(path: string): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url);

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `API request failed (${res.status}) ${url}${text ? `: ${text}` : ""}`
    );
  }

  return res.json();
}

async function patchJson<T>(path: string, body?: unknown): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `API request failed (${res.status}) ${url}${text ? `: ${text}` : ""}`
    );
  }

  return res.json();
}

async function deleteJson(path: string): Promise<void> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url, { method: "DELETE" });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `API request failed (${res.status}) ${url}${text ? `: ${text}` : ""}`
    );
  }
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `API request failed (${res.status}) ${url}${text ? `: ${text}` : ""}`
    );
  }

  return res.json();
}

/**
 * Centralized API surface
 */
export const api = {
  /**
   * Lightweight connectivity check.
   * FastAPI always exposes /docs in dev.
   */
  ping: async (): Promise<boolean> => {
    try {
      const base = getApiBaseUrl();
      const res = await fetch(`${base}/ping`);
      return res.ok;
    } catch {
      return false;
    }
  },

  getProjects: () => getJson<any>("/projects"),
  getSkills: () => getJson<any>("/skills"),
  getProject: (Name: string | number) =>
    getJson<any>(`/projects/${encodeURIComponent(String(Name))}`),

  getResume: (resumeId: string | number) =>
    getJson<any>(`/resume/${encodeURIComponent(String(resumeId))}`),

  generateResume: (payload: {
    project_names: string[];
    user_config_id?: number | null;
  }) => postJson<any>("/resume/generate", payload),

  // Portfolio endpoints
  getPortfolios: () => getJson<any>("/portfolio"),

  getPortfolio: (id: string | number) =>
    getJson<any>(`/portfolio/${id}`),

  generatePortfolio: (payload: {
    project_names: string[];
    portfolio_title?: string;
  }) => postJson<any>("/portfolio/generate", payload),

  refreshPortfolio: (id: string | number) =>
    postJson<any>(`/portfolio/${id}/refresh`),

  editPortfolio: (
    id: string | number,
    payload: { title?: string; project_ids_include?: string[] }
  ) => postJson<any>(`/portfolio/${id}/edit`, payload),

  deletePortfolio: (id: string | number) =>
    deleteJson(`/portfolio/${id}`),

  getPortfolioCards: (
    id: string | number,
    filters?: { themes?: string; tones?: string; tags?: string; skills?: string }
  ) => {
    const params = new URLSearchParams();
    if (filters?.themes) params.set("themes", filters.themes);
    if (filters?.tones) params.set("tones", filters.tones);
    if (filters?.tags) params.set("tags", filters.tags);
    if (filters?.skills) params.set("skills", filters.skills);
    const qs = params.toString();
    return getJson<any>(`/portfolio/${id}/cards${qs ? `?${qs}` : ""}`);
  },

  patchPortfolioCard: (
    portfolioId: string | number,
    projectName: string,
    payload: {
      title_override?: string | null;
      summary_override?: string | null;
      tags_override?: string[] | null;
    }
  ) =>
    patchJson<any>(
      `/portfolio/${portfolioId}/cards/${encodeURIComponent(projectName)}`,
      payload
    ),

  setPortfolioCardShowcase: (
    portfolioId: string | number,
    projectName: string,
    is_showcase: boolean
  ) =>
    postJson<any>(
      `/portfolio/${portfolioId}/cards/${encodeURIComponent(projectName)}/showcase`,
      { is_showcase }
    ),

  editPortfolioBlock: (
    portfolioId: string | number,
    sectionId: string,
    blockTag: string,
    payload: Record<string, unknown>
  ) =>
    postJson<any>(
      `/portfolio/${portfolioId}/sections/${sectionId}/block/${blockTag}/edit`,
      payload
    ),

  getPortfolioConflicts: (id: string | number) =>
    getJson<any>(`/portfolio/${id}/conflicts`),

  exportPortfolio: async (id: string | number): Promise<Blob> => {
    const base = getApiBaseUrl();
    const url = `${base}/portfolio/${id}/export`;
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(
        `API request failed (${res.status}) ${url}${text ? `: ${text}` : ""}`
      );
    }
    return res.blob();
  },
};