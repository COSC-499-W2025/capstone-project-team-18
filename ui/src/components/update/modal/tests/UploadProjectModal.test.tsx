import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import UploadProjectModal from "../UploadProjectModal";
import { api } from "../../../../api/apiClient";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../../../../api/apiClient", () => ({
  api: {
    getUserConfig: vi.fn(),
  },
}));

const configWithConsent = { consent: true, github: "testuser" };
const configWithoutConsent = { consent: false, github: "" };

describe("UploadProjectModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getUserConfig).mockResolvedValue(configWithConsent as any);
  });

  it("does not render when open is false", () => {
    render(<UploadProjectModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByText("Upload Project")).not.toBeInTheDocument();
  });

  it("renders after consent is confirmed", async () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);
    expect(await screen.findByText("Upload Project")).toBeInTheDocument();
    expect(screen.getByText(/upload or drag and drop/i)).toBeInTheDocument();
  });

  it("does not render content while consent check is pending", () => {
    vi.mocked(api.getUserConfig).mockReturnValue(new Promise(() => {}));
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);
    expect(screen.queryByText("Upload Project")).not.toBeInTheDocument();
  });

  it("closes and redirects to profile when consent is missing", async () => {
    vi.mocked(api.getUserConfig).mockResolvedValue(configWithoutConsent as any);
    const onClose = vi.fn();

    render(<UploadProjectModal open={true} onClose={onClose} />);

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(mockNavigate).toHaveBeenCalledWith("/profile", {
      state: { consentRequired: true },
    });
    expect(screen.queryByText("Upload Project")).not.toBeInTheDocument();
  });

  it("keeps Start Mining disabled until a valid file is selected", async () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);
    const btn = await screen.findByRole("button", { name: /start mining/i });
    expect(btn).toBeDisabled();
  });

  it("shows selected file name after a valid file is chosen", async () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);
    await screen.findByText("Upload Project");

    fireEvent.change(screen.getByTestId("upload-input") as HTMLInputElement, {
      target: { files: [new File(["x"], "project.zip", { type: "application/zip" })] },
    });

    expect(screen.getByText("project.zip")).toBeInTheDocument();
  });

  it("keeps Start Mining disabled and shows an error for unsupported file types", async () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);
    await screen.findByText("Upload Project");

    fireEvent.change(screen.getByTestId("upload-input") as HTMLInputElement, {
      target: { files: [new File(["x"], "project.txt", { type: "text/plain" })] },
    });

    expect(screen.getByText(/unsupported file type/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start mining/i })).toBeDisabled();
  });

  it("calls onUploadSuccess with the file and closes when Start Mining is clicked", async () => {
    const onClose = vi.fn();
    const onUploadSuccess = vi.fn();
    render(
      <UploadProjectModal open={true} onClose={onClose} onUploadSuccess={onUploadSuccess} />
    );
    await screen.findByText("Upload Project");

    const file = new File(["x"], "project.zip", { type: "application/zip" });
    fireEvent.change(screen.getByTestId("upload-input") as HTMLInputElement, {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: /start mining/i }));

    expect(onClose).toHaveBeenCalled();
    expect(onUploadSuccess).toHaveBeenCalledWith(file);
  });
});
