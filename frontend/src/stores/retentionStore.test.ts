/**
 * Retention Store Tests
 */
import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useRetentionStore } from "./retentionStore";
import type {
  RetentionPolicyFormData,
  RetentionSimulation,
} from "../types/retention";

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

// Reset store between tests
beforeEach(() => {
  act(() => {
    // Reset to initial state
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
    it("should add a new policy", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy(
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

    it("should generate unique IDs for policies", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy(
          createTestPolicyData({
            name: "Policy 1",
            dataType: "measurement_set",
          })
        );
        result.current.addPolicy(
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
    it("should update an existing policy", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy(
          createTestPolicyData({
            name: "Original Name",
            status: "active",
          })
        );
      });

      const policyId = result.current.policies[0].id;

      act(() => {
        result.current.updatePolicy(policyId, {
          name: "Updated Name",
          status: "paused",
        });
      });

      expect(result.current.policies[0].name).toBe("Updated Name");
      expect(result.current.policies[0].status).toBe("paused");
    });

    it("should not modify other policies", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy(
          createTestPolicyData({
            name: "Policy 1",
            dataType: "measurement_set",
          })
        );
        result.current.addPolicy(
          createTestPolicyData({
            name: "Policy 2",
            dataType: "image",
          })
        );
      });

      const policy1Id = result.current.policies[0].id;

      act(() => {
        result.current.updatePolicy(policy1Id, { name: "Updated" });
      });

      expect(result.current.policies[1].name).toBe("Policy 2");
    });
  });

  describe("deletePolicy", () => {
    it("should remove a policy", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy(
          createTestPolicyData({
            name: "To Delete",
          })
        );
      });

      const policyId = result.current.policies[0].id;

      act(() => {
        result.current.deletePolicy(policyId);
      });

      expect(result.current.policies).toHaveLength(0);
    });
  });

  describe("runSimulation", () => {
    it("should run a simulation and store results", async () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy(
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

      act(() => {
        result.current.addPolicy(createTestPolicyData({ name: "Test Policy" }));
      });

      const policyId = result.current.policies[0].id;

      // Start simulation but don't await
      let simulationPromise: Promise<RetentionSimulation>;
      act(() => {
        simulationPromise = result.current.runSimulation(policyId);
      });

      // Should be simulating
      expect(result.current.isSimulating).toBe(true);

      // Wait for completion
      await act(async () => {
        await simulationPromise;
      });

      expect(result.current.isSimulating).toBe(false);
    });
  });

  describe("executePolicy", () => {
    it("should execute a policy and store results", async () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy(
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

      act(() => {
        result.current.addPolicy(createTestPolicyData({ name: "Test Policy" }));
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
