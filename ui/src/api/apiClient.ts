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
  // Vitest/Node-friendly override
  const nodeEnvBase = typeof process !== "undefined" ? process.env.VITE_API_BASE_URL : undefined;

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
    const res = await fetch(`${base}/projects`);
    return res.ok;
  } catch {
    return false;
  }
},

  getProjects: () => getJson<any>("/projects"),

  getSkills: () => getJson<any>("/skills")
};