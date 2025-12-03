/**
 * Retention Store Tests
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useRetentionStore } from "./retentionStore";
import type {
  RetentionPolicy,
  RetentionPolicyFormData,
  RetentionSimulation,
} from "../types/retention";

// Mock the API functions
vi.mock("../api/retention", () => ({
  listRetentionPolicies: vi.fn(),
  createRetentionPolicy: vi.fn(),
  updateRetentionPolicy: vi.fn(),
  deleteRetentionPolicy: vi.fn(),
  simulateRetentionPolicy: vi.fn(),
  executeRetentionPolicy: vi.fn(),
  listRetentionExecutions: vi.fn(),
}));

// Import mocked functions
import {
  createRetentionPolicy,
  updateRetentionPolicy,
  deleteRetentionPolicy,
  simulateRetentionPolicy,
  executeRetentionPolicy,
} from "../api/retention";

const mockCreateRetentionPolicy = createRetentionPolicy as ReturnType<
  typeof vi.fn
>;
const mockUpdateRetentionPolicy = updateRetentionPolicy as ReturnType<
  typeof vi.fn
>;
const mockDeleteRetentionPolicy = deleteRetentionPolicy as ReturnType<
  typeof vi.fn
>;
const mockSimulateRetentionPolicy = simulateRetentionPolicy as ReturnType<
  typeof vi.fn
>;
const mockExecuteRetentionPolicy = executeRetentionPolicy as ReturnType<
  typeof vi.fn
>;

// Counter for generating unique IDs
let idCounter = 0;

// Helper to create a mock policy response
function createMockPolicy(data: RetentionPolicyFormData): RetentionPolicy {
  idCounter++;
  return {
    id: `policy-${idCounter}`,
    name: data.name,
    description: data.description || "",
    dataType: data.dataType,
    priority: data.priority,
    status: data.status,
    rules: data.rules,
    requireConfirmation: data.requireConfirmation,
    createBackupBeforeDelete: data.createBackupBeforeDelete,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}
// Helper to create valid form data
function createTestPolicyData(
  overrides: Partial<RetentionPolicyFormData> = {}
): RetentionPolicyFormData {
  return {
    name: "Test Policy",
    description: "Test description",
    dataType: "measurement_set",
    priority: "medium",
    status: "active",
    rules: [],
    requireConfirmation: false,
    createBackupBeforeDelete: false,
    ...overrides,
  };
}

// Reset store and mocks between tests
beforeEach(() => {
  // Reset ID counter
  idCounter = 0;

  // Clear all mocks
  vi.clearAllMocks();

  // Setup default mock implementations
  mockCreateRetentionPolicy.mockImplementation(async (data) =>
    createMockPolicy(data)
  );
  mockUpdateRetentionPolicy.mockImplementation(async (id, data) => ({
    id,
    ...data,
    updatedAt: new Date().toISOString(),
  }));
  mockDeleteRetentionPolicy.mockResolvedValue(undefined);
  mockSimulateRetentionPolicy.mockImplementation(async (id) => ({
    policyId: id,
    targetedItems: [],
    totalSize: 0,
    totalCount: 0,
    executionTime: 0,
  }));
  mockExecuteRetentionPolicy.mockImplementation(async (id) => ({
    id: `exec-${Date.now()}`,
    policyId: id,
    status: "completed",
    startedAt: new Date().toISOString(),
    completedAt: new Date().toISOString(),
    itemsProcessed: 0,
    itemsDeleted: 0,
    bytesFreed: 0,
    errors: [],
  }));

  // Reset store state
  act(() => {
    useRetentionStore.setState({
      policies: [],
      simulations: {},
      executions: [],
      isSimulating: false,
      isExecuting: false,
      isLoading: false,
      error: null,
      selectedPolicyId: null,
      filter: {},
    });
  });
});

describe("useRetentionStore", () => {
  describe("initial state", () => {
    it("should have empty policies by default", () => {
      const { result } = renderHook(() => useRetentionStore());
      expect(result.current.policies).toEqual([]);
    });

    it("should not be loading by default", () => {
      const { result } = renderHook(() => useRetentionStore());
      expect(result.current.isLoading).toBe(false);
    });

    it("should have no error by default", () => {
      const { result } = renderHook(() => useRetentionStore());
      expect(result.current.error).toBeNull();
    });
  });

  describe("addPolicy", () => {
    it("should add a new policy", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Test Policy",
            rules: [
              {
                name: "Age Rule",
                triggerType: "age",
                threshold: 30,
                thresholdUnit: "days",
                action: "delete",
                enabled: true,
              },
            ],
          })
        );
      });

      expect(result.current.policies).toHaveLength(1);
      expect(result.current.policies[0].name).toBe("Test Policy");
      expect(result.current.policies[0].id).toBeDefined();
    });

    it("should generate unique IDs for policies", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Policy 1",
            dataType: "measurement_set",
          })
        );
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Policy 2",
            dataType: "image",
          })
        );
      });

      expect(result.current.policies[0].id).not.toBe(
        result.current.policies[1].id
      );
    });
  });

  describe("updatePolicy", () => {
    it("should update an existing policy", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Original Name",
            status: "active",
          })
        );
      });

      const policyId = result.current.policies[0].id;

      // Setup mock for the update to return merged data
      mockUpdateRetentionPolicy.mockResolvedValueOnce({
        ...result.current.policies[0],
        name: "Updated Name",
        status: "paused",
        updatedAt: new Date().toISOString(),
      });

      await act(async () => {
        await result.current.updatePolicy(policyId, {
          name: "Updated Name",
          status: "paused",
        });
      });

      expect(result.current.policies[0].name).toBe("Updated Name");
      expect(result.current.policies[0].status).toBe("paused");
    });

    it("should not modify other policies", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Policy 1",
            dataType: "measurement_set",
          })
        );
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Policy 2",
            dataType: "image",
          })
        );
      });

      const policy1Id = result.current.policies[0].id;

      // Setup mock for the update
      mockUpdateRetentionPolicy.mockResolvedValueOnce({
        ...result.current.policies[0],
        name: "Updated",
        updatedAt: new Date().toISOString(),
      });

      await act(async () => {
        await result.current.updatePolicy(policy1Id, { name: "Updated" });
      });

      expect(result.current.policies[1].name).toBe("Policy 2");
    });
  });

  describe("deletePolicy", () => {
    it("should remove a policy", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({
            name: "To Delete",
          })
        );
      });

      const policyId = result.current.policies[0].id;

      await act(async () => {
        await result.current.deletePolicy(policyId);
      });

      expect(result.current.policies).toHaveLength(0);
    });
  });

  describe("runSimulation", () => {
    it("should run a simulation and store results", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Test Policy",
            rules: [
              {
                name: "Age Rule",
                triggerType: "age",
                threshold: 30,
                thresholdUnit: "days",
                action: "delete",
                enabled: true,
              },
            ],
          })
        );
      });

      const policyId = result.current.policies[0].id;

      await act(async () => {
        await result.current.runSimulation(policyId);
      });

      expect(result.current.simulations[policyId]).toBeDefined();
      expect(result.current.simulations[policyId].policyId).toBe(policyId);
    });

    it("should set simulating state during simulation", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({ name: "Test Policy" })
        );
      });

      const policyId = result.current.policies[0].id;

      // Make the simulation take a bit of time
      let resolveSimulation: (value: RetentionSimulation) => void;
      mockSimulateRetentionPolicy.mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSimulation = resolve;
          })
      );

      // Start simulation but don't await
      let simulationPromise: Promise<RetentionSimulation>;
      act(() => {
        simulationPromise = result.current.runSimulation(policyId);
      });

      // Should be simulating
      expect(result.current.isSimulating).toBe(true);

      // Resolve the simulation
      await act(async () => {
        resolveSimulation!({
          policyId,
          targetedItems: [],
          totalSize: 0,
          totalCount: 0,
          executionTime: 0,
        });
        await simulationPromise;
      });

      expect(result.current.isSimulating).toBe(false);
    });
  });

  describe("executePolicy", () => {
    it("should execute a policy and store results", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({
            name: "Test Policy",
            rules: [
              {
                name: "Age Rule",
                triggerType: "age",
                threshold: 30,
                thresholdUnit: "days",
                action: "delete",
                enabled: true,
              },
            ],
          })
        );
      });

      const policyId = result.current.policies[0].id;

      await act(async () => {
        await result.current.executePolicy(policyId);
      });

      // Executions is an array, find by policyId
      const execution = result.current.executions.find(
        (e) => e.policyId === policyId
      );
      expect(execution).toBeDefined();
      expect(execution?.policyId).toBe(policyId);
    });

    it("should update lastExecutedAt on the policy", async () => {
      const { result } = renderHook(() => useRetentionStore());

      await act(async () => {
        await result.current.addPolicy(
          createTestPolicyData({ name: "Test Policy" })
        );
      });

      const policyId = result.current.policies[0].id;
      const beforeRun = result.current.policies[0].lastExecutedAt;

      await act(async () => {
        await result.current.executePolicy(policyId);
      });

      expect(result.current.policies[0].lastExecutedAt).not.toBe(beforeRun);
    });
  });

  describe("setError", () => {
    it("should set and be able to clear error via setState", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        useRetentionStore.setState({ error: "Test error" });
      });

      expect(result.current.error).toBe("Test error");

      act(() => {
        useRetentionStore.setState({ error: null });
      });

      expect(result.current.error).toBeNull();
    });
  });
});
