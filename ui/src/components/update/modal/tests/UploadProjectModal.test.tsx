import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import UploadProjectModal from "../UploadProjectModal";

describe("UploadProjectModal", () => {
  it("does not render when open is false", () => {
    render(<UploadProjectModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByText("Upload Projects")).not.toBeInTheDocument();
  });

  it("renders when open is true", () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);
    expect(screen.getByText("Upload Projects")).toBeInTheDocument();
    expect(screen.getByText(/upload or drag and drop/i)).toBeInTheDocument();
  });

  it("keeps Upload disabled until a valid file is selected", () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);

    const uploadButton = screen.getByRole("button", { name: /^upload$/i });
    expect(uploadButton).toBeDisabled();
  });

  it("shows selected file name after file selection", () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);

    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = new File(["dummy"], "project.zip", {
      type: "application/zip",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText("project.zip")).toBeInTheDocument();
  });

  it("keeps Upload disabled for unsupported file types", () => {
    render(<UploadProjectModal open={true} onClose={vi.fn()} />);

    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = new File(["dummy"], "project.txt", {
      type: "text/plain",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(
      screen.getByText(/unsupported file type/i)
    ).toBeInTheDocument();

    const uploadButton = screen.getByRole("button", { name: /^upload$/i });
    expect(uploadButton).toBeDisabled();
  });
});