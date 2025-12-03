/**
 * RetentionSimulationPanel Component
 *
 * Displays simulation results showing what data would be affected by a retention policy.
 */

import React from "react";
import { formatDistanceToNow } from "date-fns";
import type {
  RetentionSimulation,
  RetentionCandidate,
} from "../../types/retention";
import { formatBytes, ACTION_LABELS } from "../../types/retention";

interface RetentionSimulationPanelProps {
  /** Simulation results to display */
  simulation: RetentionSimulation | undefined;
  /** Whether simulation is running */
  isSimulating: boolean;
  /** Callback to run simulation */
  onRunSimulation: () => void;
  /** Callback to clear simulation */
  onClearSimulation: () => void;
  /** Callback to execute policy (after simulation) */
  onExecute?: () => void;
  /** Whether execution is in progress */
  isExecuting?: boolean;
  /** Policy name for display */
  policyName?: string;
}

/**
 * Action badge colors
 */
const actionColors: Record<string, string> = {
  delete: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  archive: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  compress:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  notify: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
};

export function RetentionSimulationPanel({
  simulation,
  isSimulating,
  onRunSimulation,
  onClearSimulation,
  onExecute,
  isExecuting = false,
  policyName,
}: RetentionSimulationPanelProps) {
  const [showAllCandidates, setShowAllCandidates] = React.useState(false);

  const displayedCandidates = showAllCandidates
    ? simulation?.candidates || []
    : (simulation?.candidates || []).slice(0, 10);

  if (isSimulating) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <svg
              className="w-12 h-12 mx-auto mb-4 text-blue-500 animate-spin"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              Running Simulation...
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Analyzing data to determine what would be affected
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!simulation) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="text-center py-12">
          <svg
            className="w-12 h-12 mx-auto mb-4 text-gray-400 dark:text-gray-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
            No Simulation Results
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Run a simulation to preview what data would be affected
          </p>
          <button
            onClick={onRunSimulation}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Run Simulation
          </button>
        </div>
      </div>
    );
  }

  if (!simulation.success) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-red-200 dark:border-red-800">
        <div className="text-center py-8">
          <svg
            className="w-12 h-12 mx-auto mb-4 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <p className="text-lg font-medium text-red-700 dark:text-red-300">
            Simulation Failed
          </p>
          <p className="text-sm text-red-500 dark:text-red-400 mt-1">
            {simulation.errorMessage || "An unknown error occurred"}
          </p>
          <button
            onClick={onRunSimulation}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry Simulation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Simulation Results
              {policyName && (
                <span className="text-gray-500 dark:text-gray-400 font-normal">
                  {" "}
                  — {policyName}
                </span>
              )}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Simulated{" "}
              {formatDistanceToNow(new Date(simulation.simulatedAt), {
                addSuffix: true,
              })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClearSimulation}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            >
              Clear
            </button>
            <button
              onClick={onRunSimulation}
              className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg"
            >
              Re-run
            </button>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {simulation.totalItems}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Items Affected
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {formatBytes(simulation.totalSizeBytes)}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Space to Free
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {Math.ceil(simulation.estimatedDurationSeconds / 60)} min
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Est. Duration
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {simulation.warnings.length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Warnings
            </div>
          </div>
        </div>
      </div>

      {/* Action Breakdown */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          By Action
        </h4>
        <div className="flex flex-wrap gap-2">
          {Object.entries(simulation.byAction)
            .filter(([, count]) => count > 0)
            .map(([action, count]) => (
              <span
                key={action}
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  actionColors[action] || "bg-gray-100 text-gray-800"
                }`}
              >
                {ACTION_LABELS[action as keyof typeof ACTION_LABELS]}: {count}
              </span>
            ))}
        </div>
      </div>

      {/* Warnings */}
      {simulation.warnings.length > 0 && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-yellow-50 dark:bg-yellow-900/20">
          <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2 flex items-center gap-2">
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            Warnings
          </h4>
          <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
            {simulation.warnings.map((warning, index) => (
              <li key={index}>• {warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Candidates List */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Affected Items ({simulation.totalItems})
          </h4>
          {simulation.candidates.length > 10 && (
            <button
              onClick={() => setShowAllCandidates(!showAllCandidates)}
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              {showAllCandidates
                ? "Show fewer"
                : `Show all ${simulation.candidates.length}`}
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-gray-200 dark:border-gray-700">
                <th className="pb-2 font-medium text-gray-700 dark:text-gray-300">
                  Name
                </th>
                <th className="pb-2 font-medium text-gray-700 dark:text-gray-300">
                  Size
                </th>
                <th className="pb-2 font-medium text-gray-700 dark:text-gray-300">
                  Age
                </th>
                <th className="pb-2 font-medium text-gray-700 dark:text-gray-300">
                  Action
                </th>
                <th className="pb-2 font-medium text-gray-700 dark:text-gray-300">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {displayedCandidates.map((candidate) => (
                <CandidateRow key={candidate.id} candidate={candidate} />
              ))}
            </tbody>
          </table>
        </div>

        {!showAllCandidates && simulation.candidates.length > 10 && (
          <div className="mt-3 text-center text-sm text-gray-500 dark:text-gray-400">
            ... and {simulation.candidates.length - 10} more items
          </div>
        )}
      </div>

      {/* Execute Button */}
      {onExecute && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              This will{" "}
              {simulation.byAction.delete > 0 && (
                <strong>permanently delete</strong>
              )}{" "}
              {simulation.totalItems} items, freeing{" "}
              {formatBytes(simulation.totalSizeBytes)}
            </div>
            <button
              onClick={onExecute}
              disabled={isExecuting || simulation.totalItems === 0}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isExecuting && (
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              )}
              {isExecuting ? "Executing..." : "Execute Policy"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Individual candidate row component
 */
function CandidateRow({ candidate }: { candidate: RetentionCandidate }) {
  return (
    <tr className={candidate.isProtected ? "opacity-60" : ""}>
      <td className="py-2">
        <div className="flex items-center gap-2">
          <span
            className="font-mono text-xs truncate max-w-[200px]"
            title={candidate.path}
          >
            {candidate.name}
          </span>
        </div>
      </td>
      <td className="py-2 text-gray-600 dark:text-gray-400">
        {formatBytes(candidate.sizeBytes)}
      </td>
      <td className="py-2 text-gray-600 dark:text-gray-400">
        {candidate.ageDays} days
      </td>
      <td className="py-2">
        <span
          className={`px-2 py-0.5 rounded text-xs font-medium ${
            actionColors[candidate.action] || "bg-gray-100 text-gray-800"
          }`}
        >
          {ACTION_LABELS[candidate.action]}
        </span>
      </td>
      <td className="py-2">
        {candidate.isProtected ? (
          <span
            className="text-xs text-yellow-600 dark:text-yellow-400 flex items-center gap-1"
            title={candidate.protectionReason}
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
            Protected
          </span>
        ) : (
          <span className="text-xs text-green-600 dark:text-green-400">
            Ready
          </span>
        )}
      </td>
    </tr>
  );
}

export default RetentionSimulationPanel;
