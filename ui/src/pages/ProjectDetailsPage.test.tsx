import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ProjectDetailsPage from "./ProjectDetailsPage";
import { api } from "../api/apiClient";

const mockNavigate = vi.fn();

vi.mock("../api/apiClient", () => ({
  api: {
    getProject: vi.fn(),
    getProjectInsights: vi.fn(),
  },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "Insight Project" }),
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

    vi.mocked(api.getProjectInsights).mockResolvedValue({
      project_name: "Insight Project",
      insights: [
        { message: "Describe the feature you shipped." },
        { message: "Explain your ownership of the backend." },
      ],
    });
  });

  it("renders resume insights returned by the API", async () => {
    render(<ProjectDetailsPage />);

    expect(screen.getByText(/loading project details/i)).toBeInTheDocument();

    expect(await screen.findByText("Resume Insights")).toBeInTheDocument();
    expect(screen.getByText("Describe the feature you shipped.")).toBeInTheDocument();
    expect(screen.getByText("Explain your ownership of the backend.")).toBeInTheDocument();
  });

  it("renders the empty state when no insights are returned", async () => {
    vi.mocked(api.getProjectInsights).mockResolvedValue({
      project_name: "Insight Project",
      insights: [],
    });

    render(<ProjectDetailsPage />);

    expect(await screen.findByText(/no resume insights are currently available/i)).toBeInTheDocument();
  });

  it("shows a not found message when the project request fails with 404", async () => {
    vi.mocked(api.getProject).mockRejectedValue(new Error("API request failed (404) http://127.0.0.1:8000/projects/Insight%20Project"));

    render(<ProjectDetailsPage />);

    expect(await screen.findByText(/not found:/i)).toBeInTheDocument();
    expect(screen.getByText(/insight project/i)).toBeInTheDocument();
  });

  it("keeps project details visible when the insights request fails", async () => {
    vi.mocked(api.getProjectInsights).mockRejectedValue(new Error("API request failed (500) http://127.0.0.1:8000/projects/Insight%20Project/insights"));

    render(<ProjectDetailsPage />);

    expect(await screen.findByRole("heading", { name: "Insight Project" })).toBeInTheDocument();
    expect(screen.getByText(/no resume insights are currently available/i)).toBeInTheDocument();
    expect(screen.queryByText(/error:/i)).not.toBeInTheDocument();
  });

  it("lets users mark insights as useful and dismiss them", async () => {
    const user = userEvent.setup();

    render(<ProjectDetailsPage />);

    const usefulButtons = await screen.findAllByRole("button", { name: "Mark useful" });
    await user.click(usefulButtons[0]);
    expect(screen.getByRole("button", { name: "Marked useful" })).toBeInTheDocument();

    const dismissButtons = screen.getAllByRole("button", { name: "Dismiss" });
    await user.click(dismissButtons[0]);
    expect(screen.queryByText("Describe the feature you shipped.")).not.toBeInTheDocument();
  });
});
