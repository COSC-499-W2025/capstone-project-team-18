import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SettingsModal from "../SettingsModal";
import { api } from "../../../../api/apiClient";

vi.mock("../../../../api/apiClient", () => ({
  api: {
    getUserConfig: vi.fn(),
    updateUserConfig: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();

  vi.mocked(api.getUserConfig).mockResolvedValue({
    id: 1,
    github: "",
    user_email: "",
    consent: false,
    resume_config: null,
  });

  vi.mocked(api.updateUserConfig).mockResolvedValue({
    id: 1,
    github: "valid-user",
    user_email: "test@example.com",
    consent: true,
    resume_config: null,
  });
});

describe("SettingsModal", () => {
  it("does not render when open is false", () => {
    render(<SettingsModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
  });

  it("renders when open is true", async () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. paulatreides")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("your@email.com")).toBeInTheDocument();

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });
  });

  it("keeps Save disabled until valid inputs and consent are provided", async () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

    const saveButton = screen.getByRole("button", { name: /^save$/i });
    expect(saveButton).toBeDisabled();

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    const githubInput = screen.getByPlaceholderText("e.g. paulatreides");
    const emailInput = screen.getByPlaceholderText("your@email.com");
    const checkbox = screen.getByRole("checkbox");

    fireEvent.change(githubInput, { target: { value: "valid-user" } });
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });

    expect(saveButton).toBeDisabled();

    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(githubInput).toHaveValue("valid-user");
      expect(emailInput).toHaveValue("test@example.com");
      expect(saveButton).not.toBeDisabled();
    });
  });

  it("calls updateUserConfig with correct payload on save", async () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    const githubInput = screen.getByPlaceholderText("e.g. paulatreides");
    const emailInput = screen.getByPlaceholderText("your@email.com");
    const checkbox = screen.getByRole("checkbox");
    const saveButton = screen.getByRole("button", { name: /^save$/i });

    fireEvent.change(githubInput, { target: { value: "valid-user" } });
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.click(checkbox);

    await waitFor(() => expect(saveButton).not.toBeDisabled());

    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateUserConfig).toHaveBeenCalledWith({
        consent: true,
        user_email: "test@example.com",
        github: "valid-user",
        resume_config: { education: [], awards: [] },
      });
    });

    expect(await screen.findByText(/settings saved successfully/i)).toBeInTheDocument();
  });

  it("allows saving with only email and consent (no github)", async () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    const emailInput = screen.getByPlaceholderText("your@email.com");
    const checkbox = screen.getByRole("checkbox");
    const saveButton = screen.getByRole("button", { name: /^save$/i });

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.click(checkbox);

    await waitFor(() => expect(saveButton).not.toBeDisabled());

    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateUserConfig).toHaveBeenCalledWith({
        consent: true,
        user_email: "test@example.com",
        github: "",
        resume_config: { education: [], awards: [] },
      });
    });
  });

  it("shows inline validation messages for invalid github and email", async () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    const githubInput = screen.getByPlaceholderText("e.g. paulatreides");
    const emailInput = screen.getByPlaceholderText("your@email.com");

    fireEvent.change(githubInput, { target: { value: "invalid username" } });
    fireEvent.change(emailInput, { target: { value: "not-an-email" } });

    expect(
      screen.getByText(/please enter a valid github username/i)
    ).toBeInTheDocument();

    expect(
      screen.getByText(/please enter a valid email/i)
    ).toBeInTheDocument();
  });
});