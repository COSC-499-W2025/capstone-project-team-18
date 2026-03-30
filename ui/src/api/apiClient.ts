const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const LATEST_RESUME_ID_KEY = "latest_resume_id";

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

function buildUrl(path: string): string {
  const base = getApiBaseUrl();
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Extract a human-readable message from an error response.
 *  FastAPI errors have the shape `{"detail": "..."}` — prefer that over raw body. */
async function readApiError(res: Response): Promise<string> {
  try {
    const text = await res.text();
    if (!text) return "";
    try {
      const json = JSON.parse(text);
      if (typeof json?.detail === "string") return json.detail;
    } catch {
      // not JSON — fall through to raw text
    }
    return text;
  } catch {
    return "";
  }
}

async function getJson<T>(path: string): Promise<T> {
  const url = buildUrl(path);
  const res = await fetch(url);

  if (!res.ok) {
    const text = await readApiError(res);

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
    const msg = await readApiError(res);
    throw new Error(msg || `API request failed (${res.status})`);
  }

  return res.json();
}

async function deleteJson(path: string): Promise<void> {
  const url = buildUrl(path);

  const res = await fetch(url, { method: "DELETE" });

  if (!res.ok) {
    const msg = await readApiError(res);
    throw new Error(msg || `API request failed (${res.status})`);
  }
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const url = buildUrl(path);

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const msg = await readApiError(res);
    throw new Error(msg || `API request failed (${res.status})`);
  }

  return res.json();
}

async function putJson<T>(path: string, body?: unknown): Promise<T> {
  const url = buildUrl(path);

  const res = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const msg = await readApiError(res);
    throw new Error(msg || `API request failed (${res.status})`);
  }

  return res.json();
}

async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  const url = buildUrl(path);

  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const msg = await readApiError(res);
    throw new Error(msg || `API request failed (${res.status})`);
  }

  return res.json();
}

export type ResumeConfigRequest = {
  education?: string[] | null;
  awards?: string[] | null;
  skills?: string[] | null;
};

export type UserConfigResponse = {
  id: number;
  consent: boolean;
  ml_consent: boolean;
  user_email?: string | null;
  github?: string | null;
  github_connected?: boolean;
  resume_config?: {
    id: number;
    education: string[];
    awards: string[];
    skills: string[];
  } | null;
};

export type GithubLoginResponse = {
  state: string;
  authorization_url: string;
  callback_scheme: string;
};

export type GithubOauthStatusResponse = {
  state: string;
  status: "pending" | "success" | "denied" | "error";
  detail: string | null;
};

export type UpdateUserConfigPayload = {
  consent: boolean;
  ml_consent?: boolean;
  user_email: string;
  github?: string | null;
  resume_config?: ResumeConfigRequest | null;
};

export type ProjectListItem = {
  project_name: string;
  user_config_used?: number | null;
  image_data?: string | null;
  created_at?: string;
  statistic?: Record<string, unknown>;
  last_updated?: string;
};

export type ListProjectsResponse = {
  projects: ProjectListItem[];
  count: number;
};

export type ProjectInsightResponse = {
  message: string;
};

export type ProjectInsightsResponse = {
  project_name: string;
  insights: ProjectInsightResponse[];
};

export type UploadProjectResponse = {
  message: string;
};

export type ResumeItemResponse = {
  id?: number | null;
  resume_id?: number | null;
  project_name?: string | null;
  title: string;
  frameworks: string[];
  bullet_points: string[];
  start_date?: string | null;
  end_date?: string | null;
};

export type ResumeResponse = {
  id?: number | null;
  title?: string | null;
  name?: string | null;
  location?: string | null;
  email?: string | null;
  github?: string | null;
  linkedin?: string | null;
  skills: string[];
  skills_by_expertise?: SkillsByExpertise | null;
  education?: string[];
  awards?: string[];
  items: ResumeItemResponse[];
  created_at?: string | null;
  last_updated?: string | null;
};

export type ResumeListItem = {
  id: number;
  title?: string | null;
  email?: string | null;
  github?: string | null;
  created_at?: string | null;
  last_updated?: string | null;
  item_count: number;
  project_names?: string[];
};

export type SkillsByExpertise = {
  expert: string[];
  intermediate: string[];
  exposure: string[];
};

export type ResumeListResponse = {
  resumes: ResumeListItem[];
  count: number;
};

export type GenerateResumePayload = {
  project_names: string[];
  user_config_id?: number | null;
  title?: string | null;
};

export type EditResumeTitlePayload = {
  title: string | null;
};

export type EditResumeHeaderPayload = {
  title?: string | null;
  name?: string | null;
  location?: string | null;
  email?: string | null;
  github_username?: string | null;
  linkedin?: string | null;
};

export type EditResumeBulletPointPayload = {
  resume_id: number;
  item_index: number;
  new_content: string;
  append: boolean;
  bullet_point_index?: number | null;
};

export type DeleteResumeBulletPointPayload = {
  item_index: number;
  bullet_point_index: number;
};

export type EditResumeItemPayload = {
  resume_id: number;
  item_index: number;
  start_date: string; // YYYY-MM-DD
  end_date: string;   // YYYY-MM-DD
  title: string;
};

export type EditResumeFrameworksPayload = {
  item_index: number;
  frameworks: string[];
};

export type EditResumeSkillsPayload = {
  expert: string[];
  intermediate: string[];
  exposure: string[];
};

export type EditResumeEducationPayload = {
  education: string[];
};

export function getLatestResumeId(): number | null {
  try {
    const raw = window.localStorage.getItem(LATEST_RESUME_ID_KEY);
    if (!raw) return null;

    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    return null;
  }
}

export function setLatestResumeId(id: number | null | undefined): void {
  try {
    if (!id || id <= 0) return;
    window.localStorage.setItem(LATEST_RESUME_ID_KEY, String(id));
  } catch {
    // no-op
  }
}

/**
 * Centralized API surface
 */

export const api = {
  /**
   * Lightweight connectivity check.
   */
  ping: async (): Promise<boolean> => {
    try {
      const res = await fetch(buildUrl("/ping"));
      return res.ok;
    } catch {
      return false;
    }
  },

  getProjects: () => getJson<ListProjectsResponse>("/projects"),

  getSkills: () => getJson<any>("/skills"),

  getProject: (name: string | number) =>
    getJson<any>(`/projects/${encodeURIComponent(String(name))}`),

  getProjectInsights: (name: string | number) =>
    getJson<ProjectInsightsResponse>(
      `/projects/${encodeURIComponent(String(name))}/insights`
    ),

  getUserConfig: () => getJson<UserConfigResponse>("/user-config"),

  updateUserConfig: (payload: UpdateUserConfigPayload) =>
    putJson<UserConfigResponse>("/user-config", payload),

  uploadProject: (payload: {
    file: File;
  }) => {
    const formData = new FormData();
    formData.append("file", payload.file);

    return postFormData<UploadProjectResponse>("/projects/upload", formData);
  },

  getResumes: () => getJson<ResumeListResponse>("/resume"),

  deleteResume: (resumeId: number) =>
    deleteJson(`/resume/${encodeURIComponent(String(resumeId))}`),
  uploadProjectImage: (projectName: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return postFormData<{ message: string }>(
      `/projects/${encodeURIComponent(projectName)}/image`,
      formData
    );
  },

  deleteProjectImage: (projectName: string) =>
    deleteJson(`/projects/${encodeURIComponent(projectName)}/image`),

  getResume: (resumeId: string | number) =>
    getJson<ResumeResponse>(`/resume/${encodeURIComponent(String(resumeId))}`),

  generateResume: async (payload: GenerateResumePayload) => {
    const res = await postJson<ResumeResponse>("/resume/generate", payload);

    if (res?.id) {
      setLatestResumeId(res.id);
    }

    return res;
  },

  editResumeBulletPoint: async (
    resumeId: number,
    payload: EditResumeBulletPointPayload
  ) => {
    const res = await postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/bullet_point`,
      payload
    );

    if (res?.id) {
      setLatestResumeId(res.id);
    }

    return res;
  },

  deleteResumeBulletPoint: async (
    resumeId: number,
    payload: DeleteResumeBulletPointPayload
  ) => {
    const res = await postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/bullet_point/delete`,
      payload
    );

    if (res?.id) {
      setLatestResumeId(res.id);
    }

    return res;
  },

  editResumeFrameworks: async (
    resumeId: number,
    payload: EditResumeFrameworksPayload
  ) => {
    const res = await postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/frameworks`,
      payload
    );

    if (res?.id) {
      setLatestResumeId(res.id);
    }

    return res;
  },

  editResumeTitle: (resumeId: number, payload: EditResumeTitlePayload) =>
    postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/metadata`,
      payload
    ),

  editResumeHeader: (resumeId: number, payload: EditResumeHeaderPayload) =>
    postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/metadata`,
      payload
    ),

  editResumeItem: (resumeId: number, payload: EditResumeItemPayload) =>
    postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/resume_item`,
      payload
    ),

  editResumeEducation: (resumeId: number, payload: EditResumeEducationPayload) =>
    postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/education`,
      payload
    ),

  editResumeSkills: async (
    resumeId: number,
    payload: EditResumeSkillsPayload
  ) => {
    const res = await postJson<ResumeResponse>(
      `/resume/${encodeURIComponent(String(resumeId))}/edit/skills`,
      payload
    );

    if (res?.id) {
      setLatestResumeId(res.id);
    }

    return res;
  },

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
      skills?: string[];
      themes?: string[];
      tones?: string;
      frameworks?: string[];
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

  githubLogin: () => getJson<GithubLoginResponse>("/github/login"),

  githubOauthStatus: (state: string) =>
    getJson<GithubOauthStatusResponse>(`/github/oauth-status?state=${encodeURIComponent(state)}`),

  revokeGithubToken: () => putJson<{ message: string }>("/github/revoke_access_token"),

  exportPortfolio: async (
    id: string | number
  ): Promise<{ pagesUrl: string } | Blob> => {
    const base = getApiBaseUrl();
    const url = `${base}/portfolio/${id}/export`;
    const res = await fetch(url);
    if (!res.ok) {
      const msg = await readApiError(res);
      throw new Error(msg || `API request failed (${res.status})`);
    }
    const contentType = res.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const json = await res.json();
      return { pagesUrl: json.pages_url as string };
    }
    return res.blob();
  },
};
