import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SettingsModal from "../SettingsModal";

describe("SettingsModal", () => {
  it("does not render when open is false", () => {
    render(<SettingsModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
  });

  it("renders when open is true", () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. paulatreides")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("your@email.com")).toBeInTheDocument();
  });

  it("keeps Save disabled until valid inputs and consent are provided", () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

    const saveButton = screen.getByRole("button", { name: /^save$/i });
    expect(saveButton).toBeDisabled();

    const githubInput = screen.getByPlaceholderText("e.g. paulatreides");
    const emailInput = screen.getByPlaceholderText("your@email.com");
    const checkbox = screen.getByRole("checkbox");

    fireEvent.change(githubInput, { target: { value: "valid-user" } });
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });

    expect(saveButton).toBeDisabled();

    fireEvent.click(checkbox);

    expect(saveButton).not.toBeDisabled();
  });

  it("shows inline validation messages for invalid github and email", () => {
    render(<SettingsModal open={true} onClose={vi.fn()} />);

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