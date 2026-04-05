/**
 * Tests for ProfilePage auto-save behaviour.
 *
 * User Information fields (name, education, awards, skills) should save
 * automatically without the user pressing "Save".  Settings fields (email,
 * GitHub, consent) still require the explicit Save button.
 */
import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ProfilePage from "./ProfilePage";
import { api } from "../api/apiClient";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({
      state: null,
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultConfig = {
  name: "Alice",
  github: "alice",
  user_email: "alice@example.com",
  consent: true,
  ml_consent: false,
  github_connected: false,
  resume_config: {
    education: ["BSc CS, UBC, 2024"],
    awards: ["Dean's List"],
    skills: ["Python:Expert", "SQL:Intermediate"],
  },
};

function setup() {
  vi.useFakeTimers();
  vi.mocked(api.getUserConfig).mockResolvedValue(defaultConfig as any);
  vi.mocked(api.updateUserConfig).mockResolvedValue({} as any);
}

function teardown() {
  vi.useRealTimers();
  vi.clearAllMocks();
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ProfilePage — auto-save", () => {
  beforeEach(setup);
  afterEach(teardown);

  it("does NOT call updateUserConfig immediately on mount", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(vi.mocked(api.updateUserConfig)).not.toHaveBeenCalled();
  });

  it("auto-saves after the user edits the name field (debounced)", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); }); // finish load + suppress-flag timeout

    const nameInput = screen.getByPlaceholderText(/paul atreides/i);
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Bob" } });
    });

    // Before debounce fires — no save yet
    expect(vi.mocked(api.updateUserConfig)).not.toHaveBeenCalled();

    // Advance past the 700 ms debounce
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.name).toBe("Bob");
  });

  it("debounces rapid name changes into a single save", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const nameInput = screen.getByPlaceholderText(/paul atreides/i);

    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "B" } });
    });
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Bo" } });
    });
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Bob" } });
    });
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.name).toBe("Bob");
  });

  it("auto-saves when an education entry is added", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const eduInput = screen.getByPlaceholderText(/bsc computer science, ubc/i);
    const addButtons = screen.getAllByRole("button", { name: /^add$/i });
    const eduAddButton = addButtons[0];

    await act(async () => {
      fireEvent.change(eduInput, { target: { value: "MSc AI, UBC, 2026" } });
      fireEvent.click(eduAddButton);
    });
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.resume_config.education).toContain("MSc AI, UBC, 2026");
  });

  it("auto-saves when an education entry is removed", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    // Find and click the × next to the loaded education entry
    const removeButtons = screen.getAllByRole("button", { name: /×/ });
    await act(async () => {
      fireEvent.click(removeButtons[0]);
    });
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.resume_config.education).not.toContain("BSc CS, UBC, 2024");
  });

  it("auto-saves when an award entry is added", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const awardInput = screen.getByPlaceholderText(/dean's list/i);
    const addButtons = screen.getAllByRole("button", { name: /^add$/i });
    const awardAddButton = addButtons[1]; // second Add button is for awards

    await act(async () => {
      fireEvent.change(awardInput, { target: { value: "Best Project 2026" } });
      fireEvent.click(awardAddButton);
    });
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.resume_config.awards).toContain("Best Project 2026");
  });

  it("auto-saves when a skill is added", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const skillInput = screen.getByPlaceholderText(/e\.g\. python/i);
    const addButtons = screen.getAllByRole("button", { name: /^add$/i });
    const skillAddButton = addButtons[2]; // third Add button is for skills

    await act(async () => {
      fireEvent.change(skillInput, { target: { value: "TensorFlow" } });
      fireEvent.click(skillAddButton);
    });
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    const skillStrings: string[] = payload.resume_config.skills;
    expect(skillStrings.some((s) => s.startsWith("TensorFlow:"))).toBe(true);
  });

  it("auto-saves when a skill is removed", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    // All × buttons: edu remove (×1) + awards remove (×1) + skill remove (×2)
    // Skills are the last two
    const removeButtons = screen.getAllByRole("button", { name: /×/ });
    const skillRemoveButton = removeButtons[removeButtons.length - 2]; // first skill ×

    await act(async () => {
      fireEvent.click(skillRemoveButton);
    });
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.resume_config.skills.length).toBe(1);
  });

  it("auto-save payload includes current Settings values (email, consent)", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const nameInput = screen.getByPlaceholderText(/paul atreides/i);
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Carol" } });
    });
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalled();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.user_email).toBe("alice@example.com");
    expect(payload.consent).toBe(true);
  });

  it("Settings Save button still works independently", async () => {
    render(<ProfilePage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const saveButton = screen.getByRole("button", { name: /^save$/i });
    await act(async () => {
      fireEvent.click(saveButton);
    });

    expect(vi.mocked(api.updateUserConfig)).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.updateUserConfig).mock.calls[0][0] as any;
    expect(payload.user_email).toBe("alice@example.com");
  });
});
