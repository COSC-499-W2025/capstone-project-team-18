import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ProjectMiningProvider, useProjectMining } from "./ProjectMiningContext";
import { api } from "../api/apiClient";

vi.mock("../api/apiClient", () => ({
  api: {
    uploadProject: vi.fn(),
  },
}));

describe("ProjectMiningContext", () => {
  beforeEach(() => vi.clearAllMocks());

  it("starts with isProjectMining false", () => {
    const { result } = renderHook(() => useProjectMining(), {
      wrapper: ProjectMiningProvider,
    });
    expect(result.current.isProjectMining).toBe(false);
  });

  it("sets isProjectMining true while the upload is in flight", async () => {
    let resolve!: (v: any) => void;
    vi.mocked(api.uploadProject).mockReturnValue(new Promise((r) => { resolve = r; }));

    const { result } = renderHook(() => useProjectMining(), {
      wrapper: ProjectMiningProvider,
    });

    act(() => { result.current.startMining(new File([""], "project.zip")); });
    expect(result.current.isProjectMining).toBe(true);

    await act(async () => { resolve({ message: "ok" }); });
    expect(result.current.isProjectMining).toBe(false);
  });

  it("resets isProjectMining to false when the upload rejects", async () => {
    vi.mocked(api.uploadProject).mockRejectedValue(new Error("upload failed"));

    const { result } = renderHook(() => useProjectMining(), {
      wrapper: ProjectMiningProvider,
    });

    await act(async () => {
      result.current.startMining(new File([""], "project.zip"));
    });

    expect(result.current.isProjectMining).toBe(false);
  });

  it("ignores a second startMining call while already mining", async () => {
    let resolve!: (v: any) => void;
    vi.mocked(api.uploadProject).mockReturnValue(new Promise((r) => { resolve = r; }));

    const { result } = renderHook(() => useProjectMining(), {
      wrapper: ProjectMiningProvider,
    });

    act(() => {
      result.current.startMining(new File([""], "a.zip"));
      result.current.startMining(new File([""], "b.zip"));
    });

    expect(vi.mocked(api.uploadProject)).toHaveBeenCalledTimes(1);

    await act(async () => { resolve({ message: "ok" }); });
  });
});
