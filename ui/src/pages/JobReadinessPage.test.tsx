import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import JobReadinessPage from "./JobReadinessPage";
import { api } from "../api/apiClient";

vi.mock("../api/apiClient", () => ({
  api: {
    getResumes: vi.fn(),
    getProjects: vi.fn(),
    analyzeJobReadiness: vi.fn(),
  },
  getLatestResumeId: vi.fn(() => 2),
}));

describe("JobReadinessPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.getResumes).mockResolvedValue({
      resumes: [
        { id: 1, title: "General Resume", item_count: 3 },
        { id: 2, title: "Backend Resume", item_count: 4 },
      ],
      count: 2,
    } as any);

    vi.mocked(api.getProjects).mockResolvedValue({
      projects: [
        { project_name: "Artifact Miner" },
        { project_name: "Interview Coach" },
      ],
      count: 2,
    } as any);
  });

  it("loads evidence, submits analysis, and renders the result", async () => {
    const user = userEvent.setup();

    vi.mocked(api.analyzeJobReadiness).mockResolvedValue({
      fit_score: 78,
      summary: "You match the backend and API parts of the role, but need stronger deployment evidence.",
      strengths: [
        { rank: 1, item: "Backend API delivery", reason: "Your selected evidence shows production-style API work." },
      ],
      weaknesses: [
        { rank: 1, item: "Cloud deployment depth", reason: "The current evidence does not show deployed infrastructure ownership." },
      ],
      suggestions: [
        {
          priority: 1,
          item: "Deploy the Interview Coach service",
          reason: "A live deployment would close the strongest missing signal.",
          action_type: "deploy",
          resource_name: "Interview Coach",
          resource_type: "project",
          resource_hint: "Ship it with a public URL and README deployment notes.",
        },
      ],
    });

    render(<JobReadinessPage />);

    expect(await screen.findByText("Backend Resume")).toBeInTheDocument();

    await user.type(
      screen.getByLabelText(/job description/i),
      "Looking for a backend engineer with FastAPI, deployment, and collaboration experience."
    );

    await user.click(screen.getByLabelText("Interview Coach"));
    await user.click(screen.getByRole("button", { name: /analyze readiness/i }));

    expect(api.analyzeJobReadiness).toHaveBeenCalledWith({
      job_description: "Looking for a backend engineer with FastAPI, deployment, and collaboration experience.",
      resume_id: 2,
      project_names: ["Interview Coach"],
    });

    expect(await screen.findByText("Overall Fit")).toBeInTheDocument();
    expect(screen.getByText(/you match the backend and api parts/i)).toBeInTheDocument();
    expect(screen.getByText(/deploy the interview coach service/i)).toBeInTheDocument();
  });

  it("renders an API error returned by the analysis request", async () => {
    const user = userEvent.setup();

    vi.mocked(api.analyzeJobReadiness).mockRejectedValue(
      new Error("The request did not include enough valid evidence to analyze.")
    );

    render(<JobReadinessPage />);

    await screen.findByText("Backend Resume");
    await user.type(screen.getByLabelText(/job description/i), "Need a software engineer.");
    await user.click(screen.getByRole("button", { name: /analyze readiness/i }));

    expect(await screen.findByText(/analysis failed:/i)).toBeInTheDocument();
    expect(screen.getByText(/enough valid evidence/i)).toBeInTheDocument();
  });
});
