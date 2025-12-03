/**
 * Batch Operations Store Tests
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useBatchStore } from "../batchStore";

// Reset store between tests
beforeEach(() => {
  act(() => {
    useBatchStore.setState({
      jobs: [],
      isLoading: false,
      error: null,
    });
  });
});

describe("useBatchStore", () => {
  describe("initial state", () => {
    it("should have empty jobs by default", () => {
      const { result } = renderHook(() => useBatchStore());
      expect(result.current.jobs).toEqual([]);
    });

    it("should not be loading by default", () => {
      const { result } = renderHook(() => useBatchStore());
      expect(result.current.isLoading).toBe(false);
    });

    it("should have no error by default", () => {
      const { result } = renderHook(() => useBatchStore());
      expect(result.current.error).toBeNull();
    });
  });

  describe("submitJob", () => {
    it("should add a new job with pending status", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: { imageIds: ["img-1", "img-2"] },
        });
      });

      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].status).toBe("pending");
      expect(result.current.jobs[0].type).toBe("reimage");
    });

    it("should generate unique job IDs", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: { imageIds: ["img-1"] },
        });
        await result.current.submitJob({
          type: "export",
          params: { format: "votable" },
        });
      });

      expect(result.current.jobs[0].id).not.toBe(result.current.jobs[1].id);
    });

    it("should set createdAt timestamp", async () => {
      const { result } = renderHook(() => useBatchStore());

      const before = new Date().toISOString();

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: {},
        });
      });

      const after = new Date().toISOString();
      const createdAt = result.current.jobs[0].createdAt;

      expect(createdAt >= before).toBe(true);
      expect(createdAt <= after).toBe(true);
    });
  });

  describe("updateJobStatus", () => {
    it("should update job status", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: {},
        });
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.updateJobStatus(jobId, "running");
      });

      expect(result.current.jobs[0].status).toBe("running");
    });

    it("should update progress when provided", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: {},
        });
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.updateJobStatus(jobId, "running", 50);
      });

      expect(result.current.jobs[0].progress).toBe(50);
    });
  });

  describe("cancelJob", () => {
    it("should set job status to cancelled", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: {},
        });
      });

      const jobId = result.current.jobs[0].id;

      await act(async () => {
        await result.current.cancelJob(jobId);
      });

      expect(result.current.jobs[0].status).toBe("cancelled");
    });
  });

  describe("removeJob", () => {
    it("should remove a job from the list", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: {},
        });
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.removeJob(jobId);
      });

      expect(result.current.jobs).toHaveLength(0);
    });

    it("should only remove the specified job", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({
          type: "reimage",
          params: {},
        });
        await result.current.submitJob({
          type: "export",
          params: {},
        });
      });

      const firstJobId = result.current.jobs[0].id;

      act(() => {
        result.current.removeJob(firstJobId);
      });

      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].type).toBe("export");
    });
  });

  describe("clearCompletedJobs", () => {
    it("should remove all completed jobs", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({ type: "reimage", params: {} });
        await result.current.submitJob({ type: "export", params: {} });
      });

      act(() => {
        result.current.updateJobStatus(result.current.jobs[0].id, "completed");
      });

      act(() => {
        result.current.clearCompletedJobs();
      });

      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].status).not.toBe("completed");
    });

    it("should also remove failed and cancelled jobs", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({ type: "reimage", params: {} });
        await result.current.submitJob({ type: "export", params: {} });
        await result.current.submitJob({ type: "rating", params: {} });
        await result.current.submitJob({ type: "reimage", params: {} });
      });

      act(() => {
        result.current.updateJobStatus(result.current.jobs[0].id, "completed");
        result.current.updateJobStatus(result.current.jobs[1].id, "failed");
        result.current.updateJobStatus(result.current.jobs[2].id, "cancelled");
        // jobs[3] remains pending
      });

      act(() => {
        result.current.clearCompletedJobs();
      });

      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].status).toBe("pending");
    });
  });

  describe("getJobById", () => {
    it("should return the job with matching ID", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({ type: "reimage", params: {} });
        await result.current.submitJob({ type: "export", params: {} });
      });

      const targetId = result.current.jobs[1].id;
      const job = result.current.getJobById(targetId);

      expect(job?.id).toBe(targetId);
      expect(job?.type).toBe("export");
    });

    it("should return undefined for non-existent ID", () => {
      const { result } = renderHook(() => useBatchStore());
      const job = result.current.getJobById("non-existent");
      expect(job).toBeUndefined();
    });
  });

  describe("getJobsByStatus", () => {
    it("should return jobs matching the status", async () => {
      const { result } = renderHook(() => useBatchStore());

      await act(async () => {
        await result.current.submitJob({ type: "reimage", params: {} });
        await result.current.submitJob({ type: "export", params: {} });
        await result.current.submitJob({ type: "rating", params: {} });
      });

      act(() => {
        result.current.updateJobStatus(result.current.jobs[0].id, "running");
        result.current.updateJobStatus(result.current.jobs[1].id, "running");
      });

      const runningJobs = result.current.getJobsByStatus("running");
      expect(runningJobs).toHaveLength(2);
    });
  });

  describe("clearError", () => {
    it("should clear the error state", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        useBatchStore.setState({ error: "Test error" });
      });

      expect(result.current.error).toBe("Test error");

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});
