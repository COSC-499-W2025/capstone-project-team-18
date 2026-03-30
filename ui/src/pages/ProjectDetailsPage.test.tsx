import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ProjectDetailsPage from "./ProjectDetailsPage";
import { api } from "../api/apiClient";

const mockNavigate = vi.fn();

vi.mock("../api/apiClient", () => ({
  api: {
    getProject: vi.fn(),
  },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "Insight Project" }),
    useLocation: () => ({ state: null, pathname: "/projects/Insight%20Project", search: "", hash: "", key: "default" }),
  };
});

describe("ProjectDetailsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.getProject).mockResolvedValue({
      project_name: "Insight Project",
      created_at: "2025-01-01T00:00:00Z",
      last_updated: "2025-01-02T00:00:00Z",
      statistic: {
        PROJECT_START_DATE: "2025-01-01",
      },
    } as any);
  });

  it("shows a not found message when the project request fails with 404", async () => {
    vi.mocked(api.getProject).mockRejectedValue(new Error("API request failed (404) http://127.0.0.1:8000/projects/Insight%20Project"));

    render(<ProjectDetailsPage />);

    expect(await screen.findByText(/not found:/i)).toBeInTheDocument();
    expect(screen.getByText(/insight project/i)).toBeInTheDocument();
  });

});
