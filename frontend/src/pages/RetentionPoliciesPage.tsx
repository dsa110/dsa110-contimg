import React, { useEffect, useMemo, useState } from "react";
import { RetentionPolicyList } from "../components/retention/RetentionPolicyList";
import { RetentionPolicyEditor } from "../components/retention/RetentionPolicyEditor";
import { RetentionSimulationPanel } from "../components/retention/RetentionSimulationPanel";
import { Card, Modal, PageSkeleton } from "../components/common";
import {
  useRetention,
  useRetentionSimulation,
  useRetentionExecution,
} from "../hooks/useRetention";
import type {
  RetentionPolicy,
  RetentionPolicyFormData,
} from "../types/retention";
import { formatBytes } from "../types/retention";
import { relativeTime } from "../utils/relativeTime";

const RetentionPoliciesPage: React.FC = () => {
  const {
    policies,
    selectedPolicyId,
    selectedPolicy,
    selectPolicy,
    addPolicy,
    updatePolicy,
    deletePolicy,
    togglePolicyStatus,
    runSimulation,
    executePolicy,
    isLoading,
    isSimulating,
    isExecuting,
    error,
    fetchPolicies,
    fetchExecutions,
  } = useRetention();

  const [editorOpen, setEditorOpen] = useState(false);
  const [policyBeingEdited, setPolicyBeingEdited] = useState<RetentionPolicy | null>(null);
  const [simulatingPolicyId, setSimulatingPolicyId] = useState<string | null>(null);
  const [executingPolicyId, setExecutingPolicyId] = useState<string | null>(null);

  const {
    simulation,
    run: runSimulationForPolicy,
    clear: clearSimulationForPolicy,
    isSimulating: storeIsSimulating,
  } = useRetentionSimulation(selectedPolicyId ?? "");
  const {
    executionHistory,
    latestExecution,
  } = useRetentionExecution(selectedPolicyId ?? "");

  // Initial data load
  useEffect(() => {
    fetchPolicies().catch(() => undefined);
  }, [fetchPolicies]);

  // Refresh execution history when selection changes
  useEffect(() => {
    if (selectedPolicyId) {
      fetchExecutions(selectedPolicyId).catch(() => undefined);
    }
  }, [selectedPolicyId, fetchExecutions]);

  const openCreateEditor = () => {
    setPolicyBeingEdited(null);
    setEditorOpen(true);
  };

  const openEditEditor = (policy: RetentionPolicy) => {
    setPolicyBeingEdited(policy);
    setEditorOpen(true);
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setPolicyBeingEdited(null);
  };

  const handleSubmitPolicy = async (data: RetentionPolicyFormData) => {
    if (policyBeingEdited) {
      await updatePolicy(policyBeingEdited.id, data);
    } else {
      await addPolicy(data);
    }
    closeEditor();
  };

  const handleSimulate = async (policy: RetentionPolicy) => {
    setSimulatingPolicyId(policy.id);
    try {
      if (policy.id === selectedPolicyId) {
        await runSimulationForPolicy();
      } else {
        await runSimulation(policy.id);
      }
    } finally {
      setSimulatingPolicyId(null);
    }
  };

  const handleExecute = async (policy: RetentionPolicy) => {
    setExecutingPolicyId(policy.id);
    try {
      await executePolicy(policy.id);
      await fetchExecutions(policy.id);
    } finally {
      setExecutingPolicyId(null);
    }
  };

  const handleDeletePolicy = async (policy: RetentionPolicy) => {
    if (
      window.confirm(
        `Delete retention policy "${policy.name}"? This cannot be undone.`
      )
    ) {
      await deletePolicy(policy.id);
    }
  };

  const executionSummary = useMemo(() => {
    if (!executionHistory.length) {
      return null;
    }
    return executionHistory.slice(0, 5);
  }, [executionHistory]);

  const selectedPolicyName = selectedPolicy?.name;
  const isSelectedPolicySimulating =
    storeIsSimulating && simulatingPolicyId === selectedPolicyId;
  const isSelectedPolicyExecuting =
    isExecuting && executingPolicyId === selectedPolicyId;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            Data Retention
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Define archival policies for measurement sets, images, logs, and calibration data.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => fetchPolicies().catch(() => undefined)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={openCreateEditor}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            New Policy
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 text-red-800 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {isLoading && policies.length === 0 ? (
        <PageSkeleton variant="list" />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <RetentionPolicyList
            onSelectPolicy={(policy) => selectPolicy(policy.id)}
            selectedPolicyId={selectedPolicyId}
            onEditPolicy={openEditEditor}
            onDeletePolicy={handleDeletePolicy}
            onToggleStatus={(policy) => togglePolicyStatus(policy.id)}
            onSimulate={handleSimulate}
            onExecute={handleExecute}
            onCreatePolicy={openCreateEditor}
            simulatingPolicyId={simulatingPolicyId}
            executingPolicyId={executingPolicyId}
          />

          <div className="space-y-6">
            {selectedPolicy ? (
              <>
                <Card title="Policy Details">
                  <dl className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <dt className="text-gray-500 dark:text-gray-400">Status</dt>
                      <dd className="text-gray-900 dark:text-gray-100 capitalize">{selectedPolicy.status}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500 dark:text-gray-400">Priority</dt>
                      <dd className="text-gray-900 dark:text-gray-100 capitalize">{selectedPolicy.priority}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500 dark:text-gray-400">Created</dt>
                      <dd className="text-gray-900 dark:text-gray-100">
                        {relativeTime(selectedPolicy.createdAt)}
                      </dd>
                    </div>
                    {selectedPolicy.lastExecutedAt && (
                      <div>
                        <dt className="text-gray-500 dark:text-gray-400">Last Execution</dt>
                        <dd className="text-gray-900 dark:text-gray-100">
                          {relativeTime(selectedPolicy.lastExecutedAt)}
                        </dd>
                      </div>
                    )}
                  </dl>
                  {selectedPolicy.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-4">
                      {selectedPolicy.description}
                    </p>
                  )}
                </Card>

                <RetentionSimulationPanel
                  simulation={selectedPolicyId ? simulation : undefined}
                  isSimulating={isSelectedPolicySimulating}
                  onRunSimulation={() => handleSimulate(selectedPolicy)}
                  onClearSimulation={() =>
                    selectedPolicyId ? clearSimulationForPolicy() : undefined
                  }
                  onExecute={() => handleExecute(selectedPolicy)}
                  isExecuting={isSelectedPolicyExecuting}
                  policyName={selectedPolicyName}
                />

                <Card title="Execution History">
                  {executionSummary ? (
                    <ul className="divide-y divide-gray-200 dark:divide-gray-700 text-sm">
                      {executionSummary.map((execution) => (
                        <li key={execution.id} className="py-3 flex items-center justify-between">
                          <div>
                            <p className="text-gray-900 dark:text-gray-100">
                              {relativeTime(execution.completedAt || execution.startedAt)}
                            </p>
                            <p className="text-gray-500 dark:text-gray-400 text-xs">
                              {execution.itemsAffected} items • Freed{" "}
                              {formatBytes(execution.sizeFreedBytes)}
                            </p>
                          </div>
                          <span className="capitalize text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700">
                            {execution.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      No executions recorded for this policy.
                    </p>
                  )}
                </Card>
              </>
            ) : (
              <div className="bg-white dark:bg-gray-800 border border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-8 text-center text-gray-500 dark:text-gray-400">
                Select a retention policy to view details, simulations, and execution history.
              </div>
            )}
          </div>
        </div>
      )}

      <Modal isOpen={editorOpen} onClose={closeEditor} title={policyBeingEdited ? "Edit Policy" : "New Policy"}>
        <RetentionPolicyEditor
          policy={policyBeingEdited || undefined}
          onSubmit={handleSubmitPolicy}
          onCancel={closeEditor}
          isSubmitting={isLoading}
        />
      </Modal>
    </div>
  );
};

export default RetentionPoliciesPage;
