import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ProfilePage from "./ProfilePage";
import { api } from "../api/apiClient";

let mockLocationState: any = null;

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({
      state: mockLocationState,
      pathname: "/profile",
      search: "",
      hash: "",
      key: "default",
    }),
  };
});

vi.mock("../api/apiClient", () => ({
  api: {
    getUserConfig: vi.fn(),
    updateUserConfig: vi.fn(),
    githubLogin: vi.fn(),
    githubOauthStatus: vi.fn(),
    revokeGithubToken: vi.fn(),
  },
}));

const defaultConfig = {
  name: "Test User",
  github: "",
  user_email: "test@example.com",
  consent: false,
  ml_consent: false,
  github_connected: false,
  resume_config: { education: [], awards: [], skills: [] },
};

describe("ProfilePage — consent banner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocationState = null;
    vi.mocked(api.getUserConfig).mockResolvedValue(defaultConfig as any);
  });

  it("does not show the banner when there is no consentRequired state", () => {
    render(<ProfilePage />);
    expect(
      screen.queryByText(/you must enter your email and accept the data consent/i)
    ).not.toBeInTheDocument();
  });

  it("shows the banner when navigated with consentRequired: true", () => {
    mockLocationState = { consentRequired: true };
    render(<ProfilePage />);
    expect(
      screen.getByText(/you must enter your email and accept the data consent/i)
    ).toBeInTheDocument();
  });

  it("dismisses the banner when the × button is clicked", () => {
    mockLocationState = { consentRequired: true };
    render(<ProfilePage />);

    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));

    expect(
      screen.queryByText(/you must enter your email and accept the data consent/i)
    ).not.toBeInTheDocument();
  });

  it("dismisses the banner when the consent checkbox is checked", () => {
    mockLocationState = { consentRequired: true };
    render(<ProfilePage />);

    expect(screen.getByText(/you must enter your email and accept the data consent/i)).toBeInTheDocument();

    // The consent checkbox is the first checkbox on the page
    fireEvent.click(screen.getAllByRole("checkbox")[0]);

    expect(
      screen.queryByText(/you must enter your email and accept the data consent/i)
    ).not.toBeInTheDocument();
  });

  it("shows both the banner and the consent checkbox when consentRequired is set", () => {
    mockLocationState = { consentRequired: true };
    render(<ProfilePage />);

    expect(screen.getByText(/you must enter your email and accept the data consent/i)).toBeInTheDocument();
    // Consent checkbox is present for the user to act on
    expect(screen.getAllByRole("checkbox").length).toBeGreaterThan(0);
  });
});
