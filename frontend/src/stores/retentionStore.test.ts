/**
 * Retention Store Tests
 */
import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useRetentionStore } from "./retentionStore";

// Reset store between tests
beforeEach(() => {
  act(() => {
    // Reset to initial state
    useRetentionStore.setState({
      policies: [],
      simulations: {},
      executions: {},
      isLoading: false,
      error: null,
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
        result.current.addPolicy({
          name: "Test Policy",
          description: "Test description",
          dataType: "measurement_set",
          enabled: true,
          rules: [
            {
              triggerType: "age",
              triggerValue: 30,
              action: "delete",
            },
          ],
        });
      });

      expect(result.current.policies).toHaveLength(1);
      expect(result.current.policies[0].name).toBe("Test Policy");
      expect(result.current.policies[0].id).toBeDefined();
    });

    it("should generate unique IDs for policies", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy({
          name: "Policy 1",
          dataType: "measurement_set",
          enabled: true,
          rules: [],
        });
        result.current.addPolicy({
          name: "Policy 2",
          dataType: "image",
          enabled: true,
          rules: [],
        });
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
        result.current.addPolicy({
          name: "Original Name",
          dataType: "measurement_set",
          enabled: true,
          rules: [],
        });
      });

      const policyId = result.current.policies[0].id;

      act(() => {
        result.current.updatePolicy(policyId, {
          name: "Updated Name",
          enabled: false,
        });
      });

      expect(result.current.policies[0].name).toBe("Updated Name");
      expect(result.current.policies[0].enabled).toBe(false);
    });

    it("should not modify other policies", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy({
          name: "Policy 1",
          dataType: "measurement_set",
          enabled: true,
          rules: [],
        });
        result.current.addPolicy({
          name: "Policy 2",
          dataType: "image",
          enabled: true,
          rules: [],
        });
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
        result.current.addPolicy({
          name: "To Delete",
          dataType: "measurement_set",
          enabled: true,
          rules: [],
        });
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
        result.current.addPolicy({
          name: "Test Policy",
          dataType: "measurement_set",
          enabled: true,
          rules: [
            {
              triggerType: "age",
              triggerValue: 30,
              action: "delete",
            },
          ],
        });
      });

      const policyId = result.current.policies[0].id;

      await act(async () => {
        await result.current.runSimulation(policyId);
      });

      expect(result.current.simulations[policyId]).toBeDefined();
      expect(result.current.simulations[policyId].policyId).toBe(policyId);
    });

    it("should set loading state during simulation", async () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy({
          name: "Test Policy",
          dataType: "measurement_set",
          enabled: true,
          rules: [],
        });
      });

      const policyId = result.current.policies[0].id;

      // Start simulation but don't await
      let simulationPromise: Promise<void>;
      act(() => {
        simulationPromise = result.current.runSimulation(policyId);
      });

      // Should be loading
      expect(result.current.isLoading).toBe(true);

      // Wait for completion
      await act(async () => {
        await simulationPromise;
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("executePolicy", () => {
    it("should execute a policy and store results", async () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy({
          name: "Test Policy",
          dataType: "measurement_set",
          enabled: true,
          rules: [
            {
              triggerType: "age",
              triggerValue: 30,
              action: "delete",
            },
          ],
        });
      });

      const policyId = result.current.policies[0].id;

      await act(async () => {
        await result.current.executePolicy(policyId);
      });

      expect(result.current.executions[policyId]).toBeDefined();
      expect(result.current.executions[policyId].policyId).toBe(policyId);
    });

    it("should update lastRun on the policy", async () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        result.current.addPolicy({
          name: "Test Policy",
          dataType: "measurement_set",
          enabled: true,
          rules: [],
        });
      });

      const policyId = result.current.policies[0].id;
      const beforeRun = result.current.policies[0].lastRun;

      await act(async () => {
        await result.current.executePolicy(policyId);
      });

      expect(result.current.policies[0].lastRun).not.toBe(beforeRun);
    });
  });

  describe("clearError", () => {
    it("should clear any error", () => {
      const { result } = renderHook(() => useRetentionStore());

      act(() => {
        useRetentionStore.setState({ error: "Test error" });
      });

      expect(result.current.error).toBe("Test error");

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});
