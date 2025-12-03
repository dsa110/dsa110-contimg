/**
 * Batch Operations Store Tests
 */
import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useBatchStore } from "./batchStore";
import type { CreateBatchJobRequest } from "../types/batch";

// Helper to create valid job request
function createTestJobRequest(
  overrides: Partial<CreateBatchJobRequest> = {}
): CreateBatchJobRequest {
  return {
    operationType: "reimage",
    name: "Test Job",
    parameters: {
      type: "reimage",
      params: { robust: 0, cellSize: 2 },
    },
    resourceIds: ["img-1"],
    resourceType: "image",
    ...overrides,
  };
}

// Reset store between tests
beforeEach(() => {
  act(() => {
    useBatchStore.setState({
      jobs: [],
      filters: {},
      selectedJobId: null,
      isPanelOpen: false,
    });
  });
});

describe("useBatchStore", () => {
  describe("initial state", () => {
    it("should have empty jobs by default", () => {
      const { result } = renderHook(() => useBatchStore());
      expect(result.current.jobs).toEqual([]);
    });

    it("should have empty filters by default", () => {
      const { result } = renderHook(() => useBatchStore());
      expect(result.current.filters).toEqual({});
    });

    it("should have no selected job by default", () => {
      const { result } = renderHook(() => useBatchStore());
      expect(result.current.selectedJobId).toBeNull();
    });
  });

  describe("createJob", () => {
    it("should add a new job with pending status", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].status).toBe("pending");
      expect(result.current.jobs[0].operationType).toBe("reimage");
    });

    it("should generate unique job IDs", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 1" }));
        result.current.createJob(
          createTestJobRequest({
            name: "Job 2",
            operationType: "export",
            parameters: {
              type: "export",
              params: { format: "votable" },
            },
          })
        );
      });

      expect(result.current.jobs[0].id).not.toBe(result.current.jobs[1].id);
    });

    it("should set submittedAt timestamp", () => {
      const { result } = renderHook(() => useBatchStore());

      const before = new Date().toISOString();

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      const after = new Date().toISOString();
      const submittedAt = result.current.jobs[0].submittedAt;

      expect(submittedAt >= before).toBe(true);
      expect(submittedAt <= after).toBe(true);
    });
  });

  describe("updateJobStatus", () => {
    it("should update job status", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.updateJobStatus(jobId, "running");
      });

      expect(result.current.jobs[0].status).toBe("running");
    });

    it("should update error when provided", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.updateJobStatus(jobId, "failed", "Connection timeout");
      });

      expect(result.current.jobs[0].status).toBe("failed");
      expect(result.current.jobs[0].error).toBe("Connection timeout");
    });
  });

  describe("updateJobProgress", () => {
    it("should update job progress", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.updateJobProgress(jobId, 50, 5, 1);
      });

      expect(result.current.jobs[0].progress).toBe(50);
      expect(result.current.jobs[0].completedCount).toBe(5);
      expect(result.current.jobs[0].failedCount).toBe(1);
    });
  });

  describe("cancelJob", () => {
    it("should set job status to cancelled", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.cancelJob(jobId);
      });

      expect(result.current.jobs[0].status).toBe("cancelled");
    });
  });

  describe("removeJob", () => {
    it("should remove a job from the list", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.removeJob(jobId);
      });

      expect(result.current.jobs).toHaveLength(0);
    });

    it("should only remove the specified job", () => {
      const { result } = renderHook(() => useBatchStore());

      // Create first job
      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 1" }));
      });
      const firstJobId = result.current.jobs[0].id;

      // Create second job (will be at index 0 since it's prepended)
      act(() => {
        result.current.createJob(
          createTestJobRequest({
            name: "Job 2",
            operationType: "export",
            parameters: {
              type: "export",
              params: { format: "votable" },
            },
          })
        );
      });

      // Remove first job
      act(() => {
        result.current.removeJob(firstJobId);
      });

      expect(result.current.jobs).toHaveLength(1);
      // The remaining job should be the export job (Job 2)
      expect(result.current.jobs[0].operationType).toBe("export");
    });
  });

  describe("clearCompleted", () => {
    it("should remove all completed jobs", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 1" }));
      });
      act(() => {
        result.current.createJob(
          createTestJobRequest({
            name: "Job 2",
            operationType: "export",
            parameters: {
              type: "export",
              params: { format: "votable" },
            },
          })
        );
      });

      // Mark first created job as completed (it's at index 1 after second job prepended)
      act(() => {
        result.current.updateJobStatus(result.current.jobs[1].id, "completed");
      });

      act(() => {
        result.current.clearCompleted();
      });

      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].status).not.toBe("completed");
    });

    it("should also remove cancelled and partial jobs", () => {
      const { result } = renderHook(() => useBatchStore());

      // Create 4 jobs
      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 1" }));
      });
      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 2" }));
      });
      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 3" }));
      });
      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 4" }));
      });

      // Jobs are in reverse order: [Job4, Job3, Job2, Job1]
      // Mark statuses - note: clearCompleted removes completed, cancelled, partial (not failed)
      act(() => {
        result.current.updateJobStatus(result.current.jobs[3].id, "completed"); // Job1
        result.current.updateJobStatus(result.current.jobs[2].id, "cancelled"); // Job2
        result.current.updateJobStatus(result.current.jobs[1].id, "partial"); // Job3
        // jobs[0] (Job4) remains pending
      });

      act(() => {
        result.current.clearCompleted();
      });

      // Only Job4 (pending) should remain
      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].status).toBe("pending");
    });
  });

  describe("getJob", () => {
    it("should return the job with matching ID", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 1" }));
      });
      // Get the ID of the first job before creating second
      const firstJobId = result.current.jobs[0].id;

      act(() => {
        result.current.createJob(
          createTestJobRequest({
            name: "Job 2",
            operationType: "export",
            parameters: {
              type: "export",
              params: { format: "votable" },
            },
          })
        );
      });

      // Get the job by ID
      const job = result.current.getJob(firstJobId);

      expect(job?.id).toBe(firstJobId);
      expect(job?.operationType).toBe("reimage");
    });

    it("should return undefined for non-existent ID", () => {
      const { result } = renderHook(() => useBatchStore());
      const job = result.current.getJob("non-existent");
      expect(job).toBeUndefined();
    });
  });

  describe("getFilteredJobs", () => {
    it("should return jobs matching the filter", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest({ name: "Job 1" }));
        result.current.createJob(createTestJobRequest({ name: "Job 2" }));
        result.current.createJob(createTestJobRequest({ name: "Job 3" }));
      });

      act(() => {
        result.current.updateJobStatus(result.current.jobs[0].id, "running");
        result.current.updateJobStatus(result.current.jobs[1].id, "running");
      });

      act(() => {
        result.current.setFilters({ status: ["running"] });
      });

      const filteredJobs = result.current.getFilteredJobs();
      expect(filteredJobs).toHaveLength(2);
      expect(filteredJobs.every((j) => j.status === "running")).toBe(true);
    });
  });

  describe("selectJob", () => {
    it("should select a job", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      const jobId = result.current.jobs[0].id;

      act(() => {
        result.current.selectJob(jobId);
      });

      expect(result.current.selectedJobId).toBe(jobId);
    });

    it("should clear selection when null", () => {
      const { result } = renderHook(() => useBatchStore());

      act(() => {
        result.current.createJob(createTestJobRequest());
      });

      act(() => {
        result.current.selectJob(result.current.jobs[0].id);
      });

      act(() => {
        result.current.selectJob(null);
      });

      expect(result.current.selectedJobId).toBeNull();
    });
  });
});
