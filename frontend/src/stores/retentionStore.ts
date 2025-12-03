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
  addPolicy: (data: RetentionPolicyFormData) => RetentionPolicy;
  /** Update an existing policy */
  updatePolicy: (id: string, data: Partial<RetentionPolicyFormData>) => void;
  /** Delete a policy */
  deletePolicy: (id: string) => void;
  /** Toggle policy status (active/paused) */
  togglePolicyStatus: (id: string) => void;
  /** Set policy status */
  setPolicyStatus: (id: string, status: RetentionPolicyStatus) => void;
  /** Select a policy */
  selectPolicy: (id: string | null) => void;
  /** Get policy by ID */
  getPolicy: (id: string) => RetentionPolicy | undefined;

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
 * Demo policies for development
 */
const demoPolicies: RetentionPolicy[] = [
  {
    id: "demo-1",
    name: "Temporary Files Cleanup",
    description: "Remove temporary files older than 7 days",
    dataType: "temporary",
    priority: "high",
    status: "active",
    rules: [
      {
        id: "rule-1",
        name: "Age-based cleanup",
        description: "Delete files older than 7 days",
        triggerType: "age",
        action: "delete",
        threshold: 7,
        thresholdUnit: "days",
        enabled: true,
      },
    ],
    filePattern: "/tmp/**/*",
    requireConfirmation: false,
    createBackupBeforeDelete: false,
    createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    createdBy: "system",
    lastExecutedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    nextScheduledAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "demo-2",
    name: "Old Job Logs Archive",
    description: "Archive job logs older than 90 days",
    dataType: "job_log",
    priority: "medium",
    status: "active",
    rules: [
      {
        id: "rule-2",
        name: "Archive old logs",
        triggerType: "age",
        action: "archive",
        threshold: 90,
        thresholdUnit: "days",
        enabled: true,
      },
    ],
    requireConfirmation: true,
    createBackupBeforeDelete: false,
    createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    createdBy: "admin",
  },
  {
    id: "demo-3",
    name: "Large MS File Compression",
    description: "Compress measurement sets larger than 100GB after 30 days",
    dataType: "measurement_set",
    priority: "low",
    status: "paused",
    rules: [
      {
        id: "rule-3a",
        name: "Size threshold",
        triggerType: "size",
        action: "compress",
        threshold: 100,
        thresholdUnit: "GB",
        enabled: true,
      },
      {
        id: "rule-3b",
        name: "Age threshold",
        triggerType: "age",
        action: "compress",
        threshold: 30,
        thresholdUnit: "days",
        enabled: true,
      },
    ],
    minFileSize: 50 * 1024 * 1024 * 1024, // 50GB
    requireConfirmation: true,
    createBackupBeforeDelete: true,
    createdAt: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    createdBy: "operator",
  },
  {
    id: "demo-4",
    name: "Calibration Data Retention",
    description:
      "Keep only the 50 most recent calibration tables per calibrator",
    dataType: "calibration",
    priority: "medium",
    status: "active",
    rules: [
      {
        id: "rule-4",
        name: "Count limit",
        triggerType: "count",
        action: "archive",
        threshold: 50,
        thresholdUnit: "count",
        enabled: true,
      },
    ],
    requireConfirmation: true,
    createBackupBeforeDelete: true,
    createdAt: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    createdBy: "admin",
    lastExecutedAt: new Date(
      Date.now() - 7 * 24 * 60 * 60 * 1000
    ).toISOString(),
  },
];

/**
 * Create the retention store
 */
export const useRetentionStore = create<RetentionStore>()(
  persist(
    (set, get) => ({
      ...initialState,
      // Initialize with demo data in development
      policies: import.meta.env.DEV ? demoPolicies : [],

      // Policy management
      addPolicy: (data: RetentionPolicyFormData): RetentionPolicy => {
        const now = new Date().toISOString();
        const policy: RetentionPolicy = {
          id: generateId(),
          ...data,
          rules: data.rules.map((rule) => ({
            ...rule,
            id: generateId(),
          })),
          createdAt: now,
          updatedAt: now,
        };
        set((state) => ({
          policies: [...state.policies, policy],
        }));
        return policy;
      },

      updatePolicy: (id: string, data: Partial<RetentionPolicyFormData>) => {
        set((state) => ({
          policies: state.policies.map((policy) =>
            policy.id === id
              ? {
                  ...policy,
                  ...data,
                  rules: data.rules
                    ? data.rules.map((rule) => ({
                        ...rule,
                        id: (rule as { id?: string }).id ?? generateId(),
                      }))
                    : policy.rules,
                  updatedAt: new Date().toISOString(),
                }
              : policy
          ),
        }));
      },

      deletePolicy: (id: string) => {
        set((state) => ({
          policies: state.policies.filter((p) => p.id !== id),
          selectedPolicyId:
            state.selectedPolicyId === id ? null : state.selectedPolicyId,
          simulations: Object.fromEntries(
            Object.entries(state.simulations).filter(([key]) => key !== id)
          ),
        }));
      },

      togglePolicyStatus: (id: string) => {
        set((state) => ({
          policies: state.policies.map((policy) =>
            policy.id === id
              ? {
                  ...policy,
                  status: policy.status === "active" ? "paused" : "active",
                  updatedAt: new Date().toISOString(),
                }
              : policy
          ),
        }));
      },

      setPolicyStatus: (id: string, status: RetentionPolicyStatus) => {
        set((state) => ({
          policies: state.policies.map((policy) =>
            policy.id === id
              ? {
                  ...policy,
                  status,
                  updatedAt: new Date().toISOString(),
                }
              : policy
          ),
        }));
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

        const policy = get().getPolicy(policyId);
        if (!policy) {
          const error = "Policy not found";
          set({ isSimulating: false, error });
          throw new Error(error);
        }

        // Simulate API call delay
        await new Promise((resolve) => setTimeout(resolve, 1500));

        // Generate mock simulation results
        const candidateCount = Math.floor(Math.random() * 50) + 10;
        const candidates = Array.from({ length: candidateCount }, (_, i) => ({
          id: `candidate-${i}`,
          path: `/data/${policy.dataType}/${generateId()}.${
            policy.dataType === "image" ? "fits" : "ms"
          }`,
          name: `${policy.dataType}_${i}_${generateId().substring(0, 6)}`,
          dataType: policy.dataType,
          sizeBytes: Math.floor(Math.random() * 10 * 1024 * 1024 * 1024), // 0-10GB
          createdAt: new Date(
            Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000
          ).toISOString(),
          ageDays: Math.floor(Math.random() * 365),
          triggeredByRule: policy.rules[0]?.id || "unknown",
          action: policy.rules[0]?.action || "notify",
          isProtected: Math.random() > 0.9,
          protectionReason:
            Math.random() > 0.9 ? "Referenced by active job" : undefined,
        }));

        const totalSizeBytes = candidates.reduce(
          (sum, c) => sum + c.sizeBytes,
          0
        );

        const simulation: RetentionSimulation = {
          policyId,
          simulatedAt: new Date().toISOString(),
          candidates,
          totalItems: candidateCount,
          totalSizeBytes,
          byAction: {
            delete: candidates.filter((c) => c.action === "delete").length,
            archive: candidates.filter((c) => c.action === "archive").length,
            compress: candidates.filter((c) => c.action === "compress").length,
            notify: candidates.filter((c) => c.action === "notify").length,
          },
          byDataType: {
            measurement_set:
              policy.dataType === "measurement_set" ? candidateCount : 0,
            calibration: policy.dataType === "calibration" ? candidateCount : 0,
            image: policy.dataType === "image" ? candidateCount : 0,
            source_catalog:
              policy.dataType === "source_catalog" ? candidateCount : 0,
            job_log: policy.dataType === "job_log" ? candidateCount : 0,
            temporary: policy.dataType === "temporary" ? candidateCount : 0,
          },
          estimatedDurationSeconds: Math.ceil(candidateCount * 0.5),
          warnings:
            candidates.filter((c) => c.isProtected).length > 0
              ? [
                  `${
                    candidates.filter((c) => c.isProtected).length
                  } items are protected and will be skipped`,
                ]
              : [],
          success: true,
        };

        set((state) => ({
          isSimulating: false,
          simulations: {
            ...state.simulations,
            [policyId]: simulation,
          },
        }));

        return simulation;
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

        const policy = get().getPolicy(policyId);
        const simulation = get().getSimulation(policyId);

        if (!policy) {
          const error = "Policy not found";
          set({ isExecuting: false, error });
          throw new Error(error);
        }

        // Simulate execution
        await new Promise((resolve) => setTimeout(resolve, 2000));

        const itemsAffected =
          simulation?.candidates.filter((c) => !c.isProtected).length ||
          Math.floor(Math.random() * 30) + 5;

        const execution: RetentionExecution = {
          id: generateId(),
          policyId,
          startedAt: new Date(Date.now() - 2000).toISOString(),
          completedAt: new Date().toISOString(),
          status: "completed",
          itemsProcessed: simulation?.totalItems || itemsAffected + 5,
          itemsAffected,
          sizeFreedBytes:
            simulation?.totalSizeBytes || itemsAffected * 500 * 1024 * 1024, // ~500MB per item
          errorCount: 0,
          triggeredBy: "manual",
        };

        set((state) => ({
          isExecuting: false,
          executions: [execution, ...state.executions].slice(0, 100), // Keep last 100
          policies: state.policies.map((p) =>
            p.id === policyId
              ? { ...p, lastExecutedAt: execution.completedAt }
              : p
          ),
        }));

        return execution;
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
