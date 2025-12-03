/**
 * Retention Policy Store
 *
 * Zustand store for managing data retention policies, simulations,
 * and execution history.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  RetentionPolicy,
  RetentionPolicyFilter,
  RetentionSimulation,
  RetentionExecution,
  RetentionSummary,
  RetentionPolicyFormData,
  RetentionPolicyStatus,
} from "../types/retention";
import {
  listRetentionPolicies,
  createRetentionPolicy as apiCreateRetentionPolicy,
  updateRetentionPolicy as apiUpdateRetentionPolicy,
  deleteRetentionPolicy as apiDeleteRetentionPolicy,
  simulateRetentionPolicy,
  executeRetentionPolicy as apiExecuteRetentionPolicy,
  listRetentionExecutions,
} from "../api/retention";

/**
 * Generate a unique ID
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

/**
 * Retention store state
 */
interface RetentionState {
  /** All retention policies */
  policies: RetentionPolicy[];
  /** Currently selected policy ID */
  selectedPolicyId: string | null;
  /** Current filter settings */
  filter: RetentionPolicyFilter;
  /** Active simulations by policy ID */
  simulations: Record<string, RetentionSimulation>;
  /** Execution history */
  executions: RetentionExecution[];
  /** Whether a simulation is running */
  isSimulating: boolean;
  /** Whether an execution is running */
  isExecuting: boolean;
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
}

/**
 * Retention store actions
 */
interface RetentionActions {
  // Policy management
  /** Add a new policy */
  addPolicy: (data: RetentionPolicyFormData) => Promise<RetentionPolicy>;
  /** Update an existing policy */
  updatePolicy: (
    id: string,
    data: Partial<RetentionPolicyFormData>
  ) => Promise<void>;
  /** Delete a policy */
  deletePolicy: (id: string) => Promise<void>;
  /** Toggle policy status (active/paused) */
  togglePolicyStatus: (id: string) => Promise<void>;
  /** Set policy status */
  setPolicyStatus: (
    id: string,
    status: RetentionPolicyStatus
  ) => Promise<void>;
  /** Select a policy */
  selectPolicy: (id: string | null) => void;
  /** Get policy by ID */
  getPolicy: (id: string) => RetentionPolicy | undefined;
  /** Fetch policies/executions from backend */
  fetchPolicies: () => Promise<void>;
  /** Fetch execution history (all or specific policy) */
  fetchExecutions: (policyId?: string) => Promise<void>;

  // Filtering
  /** Set filter */
  setFilter: (filter: Partial<RetentionPolicyFilter>) => void;
  /** Clear filter */
  clearFilter: () => void;
  /** Get filtered policies */
  getFilteredPolicies: () => RetentionPolicy[];

  // Simulation
  /** Run simulation for a policy */
  runSimulation: (policyId: string) => Promise<RetentionSimulation>;
  /** Clear simulation results */
  clearSimulation: (policyId: string) => void;
  /** Get simulation for a policy */
  getSimulation: (policyId: string) => RetentionSimulation | undefined;

  // Execution
  /** Execute a policy */
  executePolicy: (policyId: string) => Promise<RetentionExecution>;
  /** Cancel a running execution */
  cancelExecution: (executionId: string) => void;
  /** Get execution history for a policy */
  getExecutionHistory: (policyId: string) => RetentionExecution[];

  // Summary
  /** Get retention summary */
  getSummary: () => RetentionSummary;

  // Utility
  /** Set loading state */
  setLoading: (loading: boolean) => void;
  /** Set error */
  setError: (error: string | null) => void;
  /** Reset store */
  reset: () => void;
}

type RetentionStore = RetentionState & RetentionActions;

/**
 * Initial state
 */
const initialState: RetentionState = {
  policies: [],
  selectedPolicyId: null,
  filter: {},
  simulations: {},
  executions: [],
  isSimulating: false,
  isExecuting: false,
  isLoading: false,
  error: null,
};

/**
 * Create the retention store
 */

/**
 * Create the retention store
 */
export const useRetentionStore = create<RetentionStore>()(
  persist(
    (set, get) => ({
      ...initialState,
      policies: [],

      // Policy management
      fetchPolicies: async () => {
        set({ isLoading: true, error: null });
        try {
          const [policies, executions] = await Promise.all([
            listRetentionPolicies(),
            listRetentionExecutions(),
          ]);
          set({
            policies,
            executions,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: getErrorMessage(
              error,
              "Failed to load retention policies from the server"
            ),
          });
          throw error;
        }
      },

      fetchExecutions: async (policyId?: string) => {
        try {
          const executions = await listRetentionExecutions(policyId);
          set((state) => {
            if (!policyId) {
              return { executions };
            }
            const remaining = state.executions.filter(
              (execution) => execution.policyId !== policyId
            );
            return {
              executions: [...executions, ...remaining],
            };
          });
        } catch (error) {
          set({
            error: getErrorMessage(
              error,
              "Failed to load retention execution history"
            ),
          });
          throw error;
        }
      },

      addPolicy: async (
        data: RetentionPolicyFormData
      ): Promise<RetentionPolicy> => {
        set({ isLoading: true, error: null });
        try {
          const policy = await apiCreateRetentionPolicy(data);
          set((state) => ({
            policies: [...state.policies, policy],
            isLoading: false,
          }));
          return policy;
        } catch (error) {
          set({
            isLoading: false,
            error: getErrorMessage(error, "Failed to create retention policy"),
          });
          throw error;
        }
      },

      updatePolicy: async (
        id: string,
        data: Partial<RetentionPolicyFormData>
      ) => {
        try {
          const updated = await apiUpdateRetentionPolicy(id, data);
          set((state) => ({
            policies: state.policies.map((policy) =>
              policy.id === id ? updated : policy
            ),
          }));
        } catch (error) {
          set({
            error: getErrorMessage(error, "Failed to update retention policy"),
          });
          throw error;
        }
      },

      deletePolicy: async (id: string) => {
        try {
          await apiDeleteRetentionPolicy(id);
          set((state) => ({
            policies: state.policies.filter((p) => p.id !== id),
            selectedPolicyId:
              state.selectedPolicyId === id ? null : state.selectedPolicyId,
            simulations: Object.fromEntries(
              Object.entries(state.simulations).filter(([key]) => key !== id)
            ),
          }));
        } catch (error) {
          set({
            error: getErrorMessage(error, "Failed to delete retention policy"),
          });
          throw error;
        }
      },

      togglePolicyStatus: async (id: string) => {
        const policy = get().getPolicy(id);
        if (!policy) return;
        const newStatus: RetentionPolicyStatus =
          policy.status === "active" ? "paused" : "active";
        await get().setPolicyStatus(id, newStatus);
      },

      setPolicyStatus: async (id: string, status: RetentionPolicyStatus) => {
        try {
          const updated = await apiUpdateRetentionPolicy(id, { status });
          set((state) => ({
            policies: state.policies.map((policy) =>
              policy.id === id ? updated : policy
            ),
          }));
        } catch (error) {
          set({
            error: getErrorMessage(
              error,
              "Failed to update retention policy status"
            ),
          });
          throw error;
        }
      },

      selectPolicy: (id: string | null) => {
        set({ selectedPolicyId: id });
      },

      getPolicy: (id: string) => {
        return get().policies.find((p) => p.id === id);
      },

      // Filtering
      setFilter: (filter: Partial<RetentionPolicyFilter>) => {
        set((state) => ({
          filter: { ...state.filter, ...filter },
        }));
      },

      clearFilter: () => {
        set({ filter: {} });
      },

      getFilteredPolicies: () => {
        const { policies, filter } = get();
        return policies.filter((policy) => {
          if (filter.status?.length && !filter.status.includes(policy.status)) {
            return false;
          }
          if (
            filter.dataType?.length &&
            !filter.dataType.includes(policy.dataType)
          ) {
            return false;
          }
          if (
            filter.priority?.length &&
            !filter.priority.includes(policy.priority)
          ) {
            return false;
          }
          if (filter.search) {
            const searchLower = filter.search.toLowerCase();
            return (
              policy.name.toLowerCase().includes(searchLower) ||
              policy.description?.toLowerCase().includes(searchLower)
            );
          }
          return true;
        });
      },

      // Simulation
      runSimulation: async (policyId: string): Promise<RetentionSimulation> => {
        set({ isSimulating: true, error: null });

        try {
          const simulation = await simulateRetentionPolicy(policyId);
          set((state) => ({
            isSimulating: false,
            simulations: {
              ...state.simulations,
              [policyId]: simulation,
            },
          }));
          return simulation;
        } catch (error) {
          set({
            isSimulating: false,
            error: getErrorMessage(
              error,
              "Failed to simulate retention policy"
            ),
          });
          throw error;
        }
      },

      clearSimulation: (policyId: string) => {
        set((state) => ({
          simulations: Object.fromEntries(
            Object.entries(state.simulations).filter(
              ([key]) => key !== policyId
            )
          ),
        }));
      },

      getSimulation: (policyId: string) => {
        return get().simulations[policyId];
      },

      // Execution
      executePolicy: async (policyId: string): Promise<RetentionExecution> => {
        set({ isExecuting: true, error: null });

        try {
          const execution = await apiExecuteRetentionPolicy(policyId);
          set((state) => ({
            isExecuting: false,
            executions: [execution, ...state.executions].slice(0, 100),
            policies: state.policies.map((p) =>
              p.id === policyId
                ? { ...p, lastExecutedAt: execution.completedAt }
                : p
            ),
          }));
          return execution;
        } catch (error) {
          set({
            isExecuting: false,
            error: getErrorMessage(
              error,
              "Failed to execute retention policy"
            ),
          });
          throw error;
        }
      },

      cancelExecution: (executionId: string) => {
        set((state) => ({
          isExecuting: false,
          executions: state.executions.map((e) =>
            e.id === executionId && e.status === "running"
              ? {
                  ...e,
                  status: "cancelled",
                  completedAt: new Date().toISOString(),
                }
              : e
          ),
        }));
      },

      getExecutionHistory: (policyId: string) => {
        return get().executions.filter((e) => e.policyId === policyId);
      },

      // Summary
      getSummary: (): RetentionSummary => {
        const { policies, executions } = get();
        const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;

        const recentExecutions = executions
          .filter(
            (e) =>
              e.status === "completed" &&
              new Date(e.completedAt || "").getTime() > thirtyDaysAgo
          )
          .slice(0, 10);

        const spaceFreedLast30Days = recentExecutions.reduce(
          (sum, e) => sum + e.sizeFreedBytes,
          0
        );

        const nextScheduled = policies
          .filter((p) => p.status === "active" && p.nextScheduledAt)
          .sort(
            (a, b) =>
              new Date(a.nextScheduledAt!).getTime() -
              new Date(b.nextScheduledAt!).getTime()
          )[0];

        return {
          totalPolicies: policies.length,
          activePolicies: policies.filter((p) => p.status === "active").length,
          pausedPolicies: policies.filter((p) => p.status === "paused").length,
          recentExecutions,
          totalManagedSpaceBytes: 0, // Would come from backend
          spaceFreedLast30Days,
          nextScheduledExecution: nextScheduled
            ? {
                policyId: nextScheduled.id,
                policyName: nextScheduled.name,
                scheduledAt: nextScheduled.nextScheduledAt!,
              }
            : undefined,
        };
      },

      // Utility
      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      setError: (error: string | null) => {
        set({ error });
      },

      reset: () => {
        set(initialState);
      },
    }),
    {
      name: "retention-store",
      partialize: (state) => ({
        policies: state.policies,
        executions: state.executions,
      }),
    }
  )
);

/**
 * Selector for selected policy
 */
export const useSelectedPolicy = () => {
  const selectedPolicyId = useRetentionStore((state) => state.selectedPolicyId);
  const getPolicy = useRetentionStore((state) => state.getPolicy);
  return selectedPolicyId ? getPolicy(selectedPolicyId) : undefined;
};

/**
 * Selector for filtered policies
 */
export const useFilteredPolicies = () => {
  return useRetentionStore((state) => state.getFilteredPolicies());
};

/**
 * Selector for retention summary
 */
export const useRetentionSummary = () => {
  return useRetentionStore((state) => state.getSummary());
};
