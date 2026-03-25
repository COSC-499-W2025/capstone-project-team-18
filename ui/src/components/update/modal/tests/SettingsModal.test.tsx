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
    ml_consent: false,
    resume_config: null,
  });

  vi.mocked(api.updateUserConfig).mockResolvedValue({
    id: 1,
    github: "valid-user",
    user_email: "test@example.com",
    consent: true,
    ml_consent: true,
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

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. paulatreides")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("your@email.com")).toBeInTheDocument();
    expect(
      screen.getByText("I also consent to ML-assisted analysis")
    ).toBeInTheDocument();
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
    const [consentCheckbox, mlConsentCheckbox] = screen.getAllByRole("checkbox");

    fireEvent.change(githubInput, { target: { value: "valid-user" } });
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });

    expect(saveButton).toBeDisabled();
    expect(mlConsentCheckbox).toBeDisabled();

    fireEvent.click(consentCheckbox);

    await waitFor(() => {
      expect(githubInput).toHaveValue("valid-user");
      expect(emailInput).toHaveValue("test@example.com");
      expect(mlConsentCheckbox).not.toBeDisabled();
      expect(saveButton).not.toBeDisabled();
    });
  });

  it("clears and disables ml consent when base consent is unchecked", async () => {
    vi.mocked(api.getUserConfig).mockResolvedValueOnce({
      id: 1,
      github: "saved-user",
      user_email: "saved@example.com",
      consent: true,
      ml_consent: true,
      resume_config: null,
    });

    render(<SettingsModal open={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    const [consentCheckbox, mlConsentCheckbox] = screen.getAllByRole("checkbox");

    expect(consentCheckbox).toBeChecked();
    expect(mlConsentCheckbox).toBeChecked();

    fireEvent.click(consentCheckbox);

    await waitFor(() => {
      expect(consentCheckbox).not.toBeChecked();
      expect(mlConsentCheckbox).not.toBeChecked();
      expect(mlConsentCheckbox).toBeDisabled();
    });
  });

  it("calls updateUserConfig with correct payload on save", async () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    const githubInput = screen.getByPlaceholderText("e.g. paulatreides");
    const emailInput = screen.getByPlaceholderText("your@email.com");
    const [consentCheckbox, mlConsentCheckbox] = screen.getAllByRole("checkbox");
    const saveButton = screen.getByRole("button", { name: /^save$/i });

    fireEvent.change(githubInput, { target: { value: "valid-user" } });
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.click(consentCheckbox);
    fireEvent.click(mlConsentCheckbox);

    await waitFor(() => expect(saveButton).not.toBeDisabled());

    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateUserConfig).toHaveBeenCalledWith({
        consent: true,
        ml_consent: true,
        user_email: "test@example.com",
        github: "valid-user",
        resume_config: { education: [], awards: [], skills: [] },
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
    const [consentCheckbox] = screen.getAllByRole("checkbox");
    const saveButton = screen.getByRole("button", { name: /^save$/i });

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.click(consentCheckbox);

    await waitFor(() => expect(saveButton).not.toBeDisabled());

    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateUserConfig).toHaveBeenCalledWith({
        consent: true,
        ml_consent: false,
        user_email: "test@example.com",
        github: "",
        resume_config: { education: [], awards: [], skills: [] },
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

  it("loads saved ML consent and renders the ML checkbox below the required consent", async () => {
    vi.mocked(api.getUserConfig).mockResolvedValueOnce({
      id: 1,
      github: "saved-user",
      user_email: "saved@example.com",
      consent: true,
      ml_consent: true,
      resume_config: null,
    });

    render(<SettingsModal open={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(api.getUserConfig).toHaveBeenCalled();
    });

    const [consentCheckbox, mlConsentCheckbox] = screen.getAllByRole("checkbox");

    expect(consentCheckbox).toBeChecked();
    expect(mlConsentCheckbox).toBeChecked();
    expect(
      screen.getByText(/i also consent to ml-assisted analysis/i)
    ).toBeInTheDocument();
  });
});
