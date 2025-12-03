/**
 * Retention Policy Hooks
 *
 * React hooks for managing retention policies, simulations, and executions.
 */

import { useCallback, useMemo } from "react";
import {
  useRetentionStore,
  useSelectedPolicy,
  useFilteredPolicies,
  useRetentionSummary,
} from "../stores/retentionStore";
import type {
  RetentionPolicy,
  RetentionPolicyFormData,
  RetentionDataType,
  RetentionPolicyStatus,
  RetentionPriority,
} from "../types/retention";

/**
 * Main hook for retention policy operations
 */
export function useRetention() {
  const {
    policies,
    selectedPolicyId,
    filter,
    simulations,
    executions,
    isSimulating,
    isExecuting,
    isLoading,
    error,
    addPolicy,
    updatePolicy,
    deletePolicy,
    togglePolicyStatus,
    setPolicyStatus,
    selectPolicy,
    getPolicy,
    setFilter,
    clearFilter,
    runSimulation,
    clearSimulation,
    getSimulation,
    executePolicy,
    cancelExecution,
    getExecutionHistory,
    setError,
    fetchPolicies,
    fetchExecutions,
  } = useRetentionStore();

  const filteredPolicies = useFilteredPolicies();
  const selectedPolicy = useSelectedPolicy();
  const summary = useRetentionSummary();

  return {
    // State
    policies,
    filteredPolicies,
    selectedPolicyId,
    selectedPolicy,
    filter,
    simulations,
    executions,
    isSimulating,
    isExecuting,
    isLoading,
    error,
    summary,

    // Policy management
    addPolicy,
    updatePolicy,
    deletePolicy,
    togglePolicyStatus,
    setPolicyStatus,
    selectPolicy,
    getPolicy,

    // Filtering
    setFilter,
    clearFilter,

    // Simulation
    runSimulation,
    clearSimulation,
    getSimulation,

    // Execution
    executePolicy,
    cancelExecution,
    getExecutionHistory,

    // Utility
    setError,
    fetchPolicies,
    fetchExecutions,
  };
}

/**
 * Hook for a specific retention policy
 */
export function useRetentionPolicy(policyId: string) {
  const {
    updatePolicy,
    deletePolicy,
    togglePolicyStatus,
    setPolicyStatus,
    runSimulation,
    clearSimulation,
    executePolicy,
    isSimulating,
    isExecuting,
  } = useRetentionStore();

  const policy = useRetentionStore(
    useCallback(
      (state) => state.policies.find((p) => p.id === policyId),
      [policyId]
    )
  );
  const simulation = useRetentionStore(
    useCallback((state) => state.simulations[policyId], [policyId])
  );
  const executionHistory = useRetentionStore(
    useCallback(
      (state) => state.executions.filter((e) => e.policyId === policyId),
      [policyId]
    )
  );

  const update = useCallback(
    (data: Partial<RetentionPolicyFormData>) => updatePolicy(policyId, data),
    [updatePolicy, policyId]
  );

  const remove = useCallback(
    () => deletePolicy(policyId),
    [deletePolicy, policyId]
  );

  const toggleStatus = useCallback(
    () => togglePolicyStatus(policyId),
    [togglePolicyStatus, policyId]
  );

  const setStatus = useCallback(
    (status: RetentionPolicyStatus) => setPolicyStatus(policyId, status),
    [setPolicyStatus, policyId]
  );

  const simulate = useCallback(
    () => runSimulation(policyId),
    [runSimulation, policyId]
  );

  const clearSim = useCallback(
    () => clearSimulation(policyId),
    [clearSimulation, policyId]
  );

  const execute = useCallback(
    () => executePolicy(policyId),
    [executePolicy, policyId]
  );

  return {
    policy,
    simulation,
    executionHistory,
    isSimulating,
    isExecuting,
    update,
    remove,
    toggleStatus,
    setStatus,
    simulate,
    clearSimulation: clearSim,
    execute,
  };
}

/**
 * Hook for filtering retention policies
 */
export function useRetentionFilter() {
  const { filter, setFilter, clearFilter } = useRetentionStore();
  const filteredPolicies = useFilteredPolicies();

  const setStatusFilter = useCallback(
    (status: RetentionPolicyStatus[]) => setFilter({ status }),
    [setFilter]
  );

  const setDataTypeFilter = useCallback(
    (dataType: RetentionDataType[]) => setFilter({ dataType }),
    [setFilter]
  );

  const setPriorityFilter = useCallback(
    (priority: RetentionPriority[]) => setFilter({ priority }),
    [setFilter]
  );

  const setSearchFilter = useCallback(
    (search: string) => setFilter({ search }),
    [setFilter]
  );

  return {
    filter,
    filteredPolicies,
    setFilter,
    clearFilter,
    setStatusFilter,
    setDataTypeFilter,
    setPriorityFilter,
    setSearchFilter,
  };
}

/**
 * Hook for retention policy simulation
 */
export function useRetentionSimulation(policyId: string) {
  const { runSimulation, clearSimulation, isSimulating, error } =
    useRetentionStore();
  const simulation = useRetentionStore(
    useCallback((state) => state.simulations[policyId], [policyId])
  );

  const run = useCallback(
    () => runSimulation(policyId),
    [runSimulation, policyId]
  );

  const clear = useCallback(
    () => clearSimulation(policyId),
    [clearSimulation, policyId]
  );

  return {
    simulation,
    isSimulating,
    error,
    run,
    clear,
  };
}

/**
 * Hook for retention policy execution
 */
export function useRetentionExecution(policyId: string) {
  const { executePolicy, cancelExecution, isExecuting, error } =
    useRetentionStore();

  const executionHistory = useRetentionStore(
    useCallback(
      (state) =>
        state.executions.filter((execution) => execution.policyId === policyId),
      [policyId]
    )
  );
  const latestExecution = executionHistory[0];

  const execute = useCallback(
    () => executePolicy(policyId),
    [executePolicy, policyId]
  );

  const cancel = useCallback(
    (executionId: string) => cancelExecution(executionId),
    [cancelExecution]
  );

  return {
    executionHistory,
    latestExecution,
    isExecuting,
    error,
    execute,
    cancel,
  };
}

/**
 * Hook for retention policies by data type
 */
export function useRetentionPoliciesByDataType(dataType: RetentionDataType) {
  const { policies } = useRetentionStore();

  return useMemo(
    () => policies.filter((p) => p.dataType === dataType),
    [policies, dataType]
  );
}

/**
 * Hook for active retention policies
 */
export function useActiveRetentionPolicies() {
  const { policies } = useRetentionStore();

  return useMemo(
    () => policies.filter((p) => p.status === "active"),
    [policies]
  );
}

/**
 * Hook for creating a new retention policy
 */
export function useCreateRetentionPolicy() {
  const { addPolicy, error, setError } = useRetentionStore();

  const create = useCallback(
    async (data: RetentionPolicyFormData): Promise<RetentionPolicy> => {
      setError(null);
      return addPolicy(data);
    },
    [addPolicy, setError]
  );

  return {
    create,
    error,
  };
}

/**
 * Hook for retention summary and statistics
 */
export function useRetentionStats() {
  const summary = useRetentionSummary();
  const { policies, executions } = useRetentionStore();

  const stats = useMemo(() => {
    const byDataType = policies.reduce((acc, p) => {
      acc[p.dataType] = (acc[p.dataType] || 0) + 1;
      return acc;
    }, {} as Record<RetentionDataType, number>);

    const byPriority = policies.reduce((acc, p) => {
      acc[p.priority] = (acc[p.priority] || 0) + 1;
      return acc;
    }, {} as Record<RetentionPriority, number>);

    // Calculate cutoff time outside the filter to avoid impure function in render
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const cutoffTime = sevenDaysAgo.getTime();

    const recentExecutionCount = executions.filter(
      (e) => new Date(e.startedAt).getTime() > cutoffTime
    ).length;

    return {
      ...summary,
      byDataType,
      byPriority,
      recentExecutionCount,
    };
  }, [summary, policies, executions]);

  return stats;
}

// Re-export for convenience
export { useSelectedPolicy, useFilteredPolicies, useRetentionSummary };
