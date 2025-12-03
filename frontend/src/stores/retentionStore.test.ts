/**
 * Retention Store Tests
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useRetentionStore } from "./retentionStore";
import type {
  RetentionPolicy,
  RetentionPolicyFormData,
  RetentionSimulation,
  RetentionExecution,
} from "../types/retention";
import {
  createRetentionPolicy as apiCreateRetentionPolicy,
  updateRetentionPolicy as apiUpdateRetentionPolicy,
  deleteRetentionPolicy as apiDeleteRetentionPolicy,
  simulateRetentionPolicy as apiSimulateRetentionPolicy,
  executeRetentionPolicy as apiExecuteRetentionPolicy,
  listRetentionPolicies as apiListRetentionPolicies,
  listRetentionExecutions as apiListRetentionExecutions,
} from "../api/retention";

vi.mock("../api/retention", () => ({
  listRetentionPolicies: vi.fn(),
  listRetentionExecutions: vi.fn(),
  createRetentionPolicy: vi.fn(),
  updateRetentionPolicy: vi.fn(),
  deleteRetentionPolicy: vi.fn(),
  simulateRetentionPolicy: vi.fn(),
  executeRetentionPolicy: vi.fn(),
}));

const mockedCreate = vi.mocked(apiCreateRetentionPolicy);
const mockedUpdate = vi.mocked(apiUpdateRetentionPolicy);
const mockedDelete = vi.mocked(apiDeleteRetentionPolicy);
const mockedSimulate = vi.mocked(apiSimulateRetentionPolicy);
const mockedExecute = vi.mocked(apiExecuteRetentionPolicy);
const mockedListPolicies = vi.mocked(apiListRetentionPolicies);
const mockedListExecutions = vi.mocked(apiListRetentionExecutions);

let idCounter = 0;

function createMockPolicy(
  data: RetentionPolicyFormData
): RetentionPolicy {
  const now = new Date().toISOString();
  idCounter += 1;
  return {
    id: `policy-${idCounter}`,
    ...data,
    description: data.description ?? "",
    rules: data.rules.map((rule, idx) => ({
      ...rule,
      id: `rule-${idCounter}-${idx}`,
    })),
    createdAt: now,
    updatedAt: now,
  };
}

function createMockSimulation(policyId: string): RetentionSimulation {
  return {
    policyId,
    simulatedAt: new Date().toISOString(),
    candidates: [],
    totalItems: 0,
    totalSizeBytes: 0,
    byAction: {
      delete: 0,
      archive: 0,
      compress: 0,
      notify: 0,
    },
    byDataType: {
      measurement_set: 0,
      calibration: 0,
      image: 0,
      source_catalog: 0,
      job_log: 0,
      temporary: 0,
    },
    estimatedDurationSeconds: 0,
    warnings: [],
    success: true,
  };
}

function createMockExecution(policyId: string): RetentionExecution {
  const now = new Date().toISOString();
  return {
    id: `exec-${policyId}`,
    policyId,
    startedAt: now,
    completedAt: now,
    status: "completed",
    itemsProcessed: 10,
    itemsAffected: 10,
    sizeFreedBytes: 1024 * 1024 * 1024,
    errorCount: 0,
    triggeredBy: "manual",
  };
}

function createTestPolicyData(
  overrides: Partial<RetentionPolicyFormData> = {}
): RetentionPolicyFormData {
  return {
    name: "Test Policy",
    description: "Test description",
    dataType: "measurement_set",
    priority: "medium",
    status: "active",
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
    requireConfirmation: false,
    createBackupBeforeDelete: false,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  idCounter = 0;

  mockedCreate.mockImplementation(async (data) => createMockPolicy(data));
  mockedUpdate.mockImplementation(async (id, data) => ({
    ...createMockPolicy({
      ...createTestPolicyData(),
      ...data,
    }),
    id,
  }));
  mockedDelete.mockResolvedValue(undefined);
  mockedSimulate.mockImplementation(async (policyId) =>
    createMockSimulation(policyId)
  );
  mockedExecute.mockImplementation(async (policyId) =>
    createMockExecution(policyId)
  );
  mockedListPolicies.mockResolvedValue([]);
  mockedListExecutions.mockResolvedValue([]);

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
  it("adds policies via the API", async () => {
    const { result } = renderHook(() => useRetentionStore());

    await act(async () => {
      await result.current.addPolicy(createTestPolicyData({ name: "Policy A" }));
    });

    expect(mockedCreate).toHaveBeenCalledTimes(1);
    expect(result.current.policies).toHaveLength(1);
    expect(result.current.policies[0].name).toBe("Policy A");
  });

  it("updates policies with API response", async () => {
    const { result } = renderHook(() => useRetentionStore());

    await act(async () => {
      await result.current.addPolicy(createTestPolicyData({ name: "Original" }));
    });

    const policyId = result.current.policies[0].id;
    mockedUpdate.mockImplementationOnce(async () =>
      createMockPolicy(createTestPolicyData({ name: "Updated" }))
    );

    await act(async () => {
      await result.current.updatePolicy(policyId, { name: "Updated" });
    });

    expect(mockedUpdate).toHaveBeenCalledWith(policyId, { name: "Updated" });
    expect(result.current.policies[0].name).toBe("Updated");
  });

  it("deletes policies", async () => {
    const { result } = renderHook(() => useRetentionStore());

    await act(async () => {
      await result.current.addPolicy(createTestPolicyData());
    });

    const policyId = result.current.policies[0].id;

    await act(async () => {
      await result.current.deletePolicy(policyId);
    });

    expect(mockedDelete).toHaveBeenCalledWith(policyId);
    expect(result.current.policies).toHaveLength(0);
  });

  it("stores simulation results from the API", async () => {
    const { result } = renderHook(() => useRetentionStore());
    await act(async () => {
      await result.current.addPolicy(createTestPolicyData());
    });
    const policyId = result.current.policies[0].id;

    const simulation = createMockSimulation(policyId);
    mockedSimulate.mockResolvedValueOnce(simulation);

    await act(async () => {
      await result.current.runSimulation(policyId);
    });

    expect(mockedSimulate).toHaveBeenCalledWith(policyId);
    expect(result.current.simulations[policyId]).toEqual(simulation);
  });

  it("records executions returned by the API", async () => {
    const { result } = renderHook(() => useRetentionStore());
    await act(async () => {
      await result.current.addPolicy(createTestPolicyData());
    });
    const policyId = result.current.policies[0].id;

    const execution = createMockExecution(policyId);
    mockedExecute.mockResolvedValueOnce(execution);

    await act(async () => {
      await result.current.executePolicy(policyId);
    });

    expect(mockedExecute).toHaveBeenCalledWith(policyId);
    expect(result.current.executions[0]).toEqual(execution);
  });
});
