/**
 * Data Cleanup Wizard Page
 *
 * Multi-step wizard for data archival/deletion:
 * 1. Select scope via filters (age, size, tags, status)
 * 2. Run dry-run to estimate impact
 * 3. Review and confirm with audit note
 * 4. Submit and track job status
 */

import React, { useState, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  useCleanupDryRun,
  useSubmitCleanup,
  useCleanupHistory,
  type CleanupFilters,
  type CleanupDryRunResult,
  type CleanupJob,
} from "../api/cleanup";
import { ROUTES } from "../constants/routes";

// Wizard step type
type WizardStep = "filters" | "preview" | "confirm" | "complete";

// Data type values
type DataType = "ms" | "image" | "log" | "temp" | "cache";

interface FilterFormState extends CleanupFilters {
  action: "archive" | "delete";
  data_type?: DataType[];
}

const defaultFilters: FilterFormState = {
  min_age_days: 30,
  data_type: ["temp", "log"],
  action: "archive",
};

function formatBytes(bytes: number): string {
  if (bytes >= 1e12) return `${(bytes / 1e12).toFixed(2)} TB`;
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(2)} KB`;
  return `${bytes} B`;
}

// Step 1: Filter Selection
function FilterStep({
  filters,
  onChange,
  onNext,
}: {
  filters: FilterFormState;
  onChange: (filters: FilterFormState) => void;
  onNext: () => void;
}) {
  const dataTypes: { value: DataType; label: string; description: string }[] = [
    {
      value: "ms",
      label: "Measurement Sets",
      description: "Raw visibility data",
    },
    { value: "image", label: "Images", description: "FITS image products" },
    { value: "log", label: "Logs", description: "Processing logs" },
    {
      value: "temp",
      label: "Temporary Files",
      description: "Intermediate data",
    },
    { value: "cache", label: "Cache", description: "Cached computations" },
  ];

  const toggleDataType = (type: DataType) => {
    const current = filters.data_type || [];
    const newTypes = current.includes(type)
      ? current.filter((t) => t !== type)
      : [...current, type];
    onChange({ ...filters, data_type: newTypes });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          Select Data to Clean Up
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Define the scope of data to include in the cleanup operation.
        </p>
      </div>

      {/* Action Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Action Type
        </label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="action"
              value="archive"
              checked={filters.action === "archive"}
              onChange={() => onChange({ ...filters, action: "archive" })}
              className="text-blue-600 focus:ring-blue-500"
            />
            <span className="text-gray-700 dark:text-gray-300">Archive</span>
            <span className="text-xs text-gray-500">
              (move to cold storage)
            </span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="action"
              value="delete"
              checked={filters.action === "delete"}
              onChange={() => onChange({ ...filters, action: "delete" })}
              className="text-red-600 focus:ring-red-500"
            />
            <span className="text-gray-700 dark:text-gray-300">Delete</span>
            <span className="text-xs text-gray-500">(permanent removal)</span>
          </label>
        </div>
        {filters.action === "delete" && (
          <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-300">
            ⚠️ Deletion is permanent and cannot be undone. Make sure you have
            backups.
          </div>
        )}
      </div>

      {/* Data Types */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Data Types
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {dataTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => toggleDataType(type.value)}
              className={`p-3 rounded-lg border text-left transition-colors ${
                filters.data_type?.includes(type.value)
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
              }`}
            >
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {type.label}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {type.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Age Filter */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label
            htmlFor="min-age-days"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Minimum Age (days)
          </label>
          <input
            id="min-age-days"
            type="number"
            value={filters.min_age_days ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                min_age_days: e.target.value
                  ? parseInt(e.target.value)
                  : undefined,
              })
            }
            min={0}
            placeholder="No minimum"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
        <div>
          <label
            htmlFor="max-age-days"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Maximum Age (days)
          </label>
          <input
            id="max-age-days"
            type="number"
            value={filters.max_age_days ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                max_age_days: e.target.value
                  ? parseInt(e.target.value)
                  : undefined,
              })
            }
            min={0}
            placeholder="No maximum"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
      </div>

      {/* Size Filter */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Minimum Size (MB)
          </label>
          <input
            type="number"
            value={filters.min_size_bytes ? filters.min_size_bytes / 1e6 : ""}
            onChange={(e) =>
              onChange({
                ...filters,
                min_size_bytes: e.target.value
                  ? parseFloat(e.target.value) * 1e6
                  : undefined,
              })
            }
            min={0}
            step={0.1}
            placeholder="No minimum"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Maximum Size (MB)
          </label>
          <input
            type="number"
            value={filters.max_size_bytes ? filters.max_size_bytes / 1e6 : ""}
            onChange={(e) =>
              onChange({
                ...filters,
                max_size_bytes: e.target.value
                  ? parseFloat(e.target.value) * 1e6
                  : undefined,
              })
            }
            min={0}
            step={0.1}
            placeholder="No maximum"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
      </div>

      {/* Path Patterns */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Include Pattern (glob)
          </label>
          <input
            type="text"
            value={filters.include_pattern ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                include_pattern: e.target.value || undefined,
              })
            }
            placeholder="e.g., /data/old/*"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Exclude Pattern (glob)
          </label>
          <input
            type="text"
            value={filters.exclude_pattern ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                exclude_pattern: e.target.value || undefined,
              })
            }
            placeholder="e.g., /data/protected/*"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono text-sm"
          />
        </div>
      </div>

      {/* Next button */}
      <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={onNext}
          disabled={!filters.data_type?.length}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Preview Impact →
        </button>
      </div>
    </div>
  );
}

// Step 2: Preview (Dry Run)
function PreviewStep({
  filters,
  dryRun,
  isLoading,
  error,
  onBack,
  onNext,
}: {
  filters: FilterFormState;
  dryRun: CleanupDryRunResult | undefined;
  isLoading: boolean;
  error: Error | null;
  onBack: () => void;
  onNext: () => void;
}) {
  if (isLoading) {
    return (
      <div className="py-12 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">
          Calculating impact...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
          <h4 className="font-medium text-red-700 dark:text-red-300 mb-1">
            Failed to calculate impact
          </h4>
          <p className="text-sm text-red-600 dark:text-red-400">
            {error.message}
          </p>
        </div>
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          ← Back to Filters
        </button>
      </div>
    );
  }

  if (!dryRun) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          Impact Preview
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Review the estimated impact before proceeding.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <div className="text-sm text-blue-600 dark:text-blue-400">
            Items Affected
          </div>
          <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
            {dryRun.affected_count.toLocaleString()}
          </div>
        </div>
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
          <div className="text-sm text-green-600 dark:text-green-400">
            Space to Reclaim
          </div>
          <div className="text-2xl font-bold text-green-700 dark:text-green-300">
            {dryRun.size_formatted}
          </div>
        </div>
        <div
          className={`rounded-lg p-4 ${
            filters.action === "delete"
              ? "bg-red-50 dark:bg-red-900/20"
              : "bg-purple-50 dark:bg-purple-900/20"
          }`}
        >
          <div
            className={`text-sm ${
              filters.action === "delete"
                ? "text-red-600 dark:text-red-400"
                : "text-purple-600 dark:text-purple-400"
            }`}
          >
            Action
          </div>
          <div
            className={`text-2xl font-bold capitalize ${
              filters.action === "delete"
                ? "text-red-700 dark:text-red-300"
                : "text-purple-700 dark:text-purple-300"
            }`}
          >
            {filters.action}
          </div>
        </div>
      </div>

      {/* Breakdown by Category */}
      {Object.keys(dryRun.by_category).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Breakdown by Category
          </h4>
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 space-y-2">
            {Object.entries(dryRun.by_category).map(([category, stats]) => (
              <div
                key={category}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-gray-700 dark:text-gray-300 capitalize">
                  {category.replace(/_/g, " ")}
                </span>
                <span className="text-gray-500 dark:text-gray-400">
                  {stats.count.toLocaleString()} items (
                  {formatBytes(stats.bytes)})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sample Paths */}
      {dryRun.sample_paths.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Sample Paths ({dryRun.sample_paths.length} of{" "}
            {dryRun.affected_count})
          </h4>
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
            <ul className="space-y-1 font-mono text-xs text-gray-600 dark:text-gray-400">
              {dryRun.sample_paths.map((path) => (
                <li key={path} className="truncate">
                  {path}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Warnings */}
      {dryRun.warnings.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
          <h4 className="font-medium text-yellow-700 dark:text-yellow-300 mb-2">
            ⚠️ Warnings
          </h4>
          <ul className="space-y-1 text-sm text-yellow-600 dark:text-yellow-400">
            {dryRun.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Retention Hints */}
      {dryRun.retention_hints && dryRun.retention_hints.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
          <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-2">
            ℹ️ Retention Policy Notes
          </h4>
          <ul className="space-y-1 text-sm text-blue-600 dark:text-blue-400">
            {dryRun.retention_hints.map((hint, i) => (
              <li key={i}>{hint}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Permission Check */}
      {!dryRun.can_execute && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h4 className="font-medium text-red-700 dark:text-red-300 mb-1">
            🚫 Permission Denied
          </h4>
          <p className="text-sm text-red-600 dark:text-red-400">
            You do not have permission to execute this cleanup operation.
            Contact an administrator for assistance.
          </p>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          ← Back to Filters
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={!dryRun.can_execute || dryRun.affected_count === 0}
          className={`px-4 py-2 rounded-lg transition-colors ${
            filters.action === "delete"
              ? "bg-red-600 text-white hover:bg-red-700"
              : "bg-blue-600 text-white hover:bg-blue-700"
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          Continue to Confirmation →
        </button>
      </div>
    </div>
  );
}

// Step 3: Confirmation
function ConfirmStep({
  filters,
  dryRun,
  auditNote,
  onAuditNoteChange,
  onBack,
  onSubmit,
  isSubmitting,
}: {
  filters: FilterFormState;
  dryRun: CleanupDryRunResult;
  auditNote: string;
  onAuditNoteChange: (note: string) => void;
  onBack: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}) {
  const [confirmed, setConfirmed] = useState(false);

  const canSubmit = confirmed && auditNote.trim().length >= 10;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          Confirm Cleanup
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Please review and confirm the cleanup operation.
        </p>
      </div>

      {/* Summary */}
      <div
        className={`rounded-lg p-4 ${
          filters.action === "delete"
            ? "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
            : "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800"
        }`}
      >
        <p
          className={`font-medium ${
            filters.action === "delete"
              ? "text-red-700 dark:text-red-300"
              : "text-blue-700 dark:text-blue-300"
          }`}
        >
          You are about to{" "}
          <span className="uppercase font-bold">{filters.action}</span>{" "}
          {dryRun.affected_count.toLocaleString()} items (
          {dryRun.size_formatted}).
        </p>
        {filters.action === "delete" && (
          <p className="text-sm text-red-600 dark:text-red-400 mt-2">
            ⚠️ This action is <strong>PERMANENT</strong> and cannot be undone.
          </p>
        )}
      </div>

      {/* Audit Note */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Audit Note <span className="text-red-500">*</span>
        </label>
        <textarea
          value={auditNote}
          onChange={(e) => onAuditNoteChange(e.target.value)}
          rows={3}
          placeholder="Explain the reason for this cleanup operation (minimum 10 characters)..."
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {auditNote.trim().length}/10 characters minimum
        </p>
      </div>

      {/* Confirmation Checkbox */}
      <label className="flex items-start gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
          className="mt-0.5 h-5 w-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
        />
        <div>
          <span className="text-gray-900 dark:text-gray-100 font-medium">
            I understand and confirm this action
          </span>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            I have reviewed the affected items and understand that{" "}
            {filters.action === "delete"
              ? "deleted data cannot be recovered"
              : "archived data will be moved to cold storage"}
            .
          </p>
        </div>
      </label>

      {/* Navigation */}
      <div className="flex justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={onBack}
          disabled={isSubmitting}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          ← Back to Preview
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={!canSubmit || isSubmitting}
          className={`px-6 py-2 rounded-lg transition-colors flex items-center gap-2 ${
            filters.action === "delete"
              ? "bg-red-600 text-white hover:bg-red-700"
              : "bg-blue-600 text-white hover:bg-blue-700"
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isSubmitting ? (
            <>
              <span className="animate-spin">⏳</span>
              Submitting...
            </>
          ) : (
            <>Submit Cleanup Job</>
          )}
        </button>
      </div>
    </div>
  );
}

// Step 4: Complete
function CompleteStep({
  job,
  onStartOver,
}: {
  job: CleanupJob;
  onStartOver: () => void;
}) {
  return (
    <div className="py-8 text-center">
      <div className="text-6xl mb-4">✅</div>
      <h3 className="text-xl font-medium text-gray-900 dark:text-gray-100 mb-2">
        Cleanup Job Submitted
      </h3>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Your cleanup job has been queued for processing.
      </p>

      <div className="inline-block bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-6 text-left">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">Job ID:</span>
            <span className="ml-2 font-mono text-gray-900 dark:text-gray-100">
              {job.id}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Status:</span>
            <span className="ml-2 text-yellow-600 dark:text-yellow-400 capitalize">
              {job.status}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Action:</span>
            <span className="ml-2 text-gray-900 dark:text-gray-100 capitalize">
              {job.action}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Submitted:</span>
            <span className="ml-2 text-gray-900 dark:text-gray-100">
              {new Date(job.submitted_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      <div className="flex justify-center gap-4">
        <Link
          to={ROUTES.JOBS.DETAIL(job.run_id)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          View Job Status
        </Link>
        <button
          type="button"
          onClick={onStartOver}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          Start New Cleanup
        </button>
      </div>
    </div>
  );
}

// Cleanup History Panel
function CleanupHistoryPanel() {
  const { data: history, isLoading, error } = useCleanupHistory(10);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-500 dark:text-red-400">
        Failed to load history
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <div className="text-4xl mb-2">📋</div>
        <div>No cleanup history</div>
      </div>
    );
  }

  const statusColors: Record<CleanupJob["status"], string> = {
    pending: "text-yellow-600 dark:text-yellow-400",
    running: "text-blue-600 dark:text-blue-400",
    completed: "text-green-600 dark:text-green-400",
    failed: "text-red-600 dark:text-red-400",
    cancelled: "text-gray-600 dark:text-gray-400",
  };

  return (
    <div className="space-y-2">
      {history.map((job) => (
        <Link
          key={job.id}
          to={ROUTES.JOBS.DETAIL(job.run_id)}
          className="block p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">
              {job.action}
            </span>
            <span className={`text-sm capitalize ${statusColors[job.status]}`}>
              {job.status}
            </span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {new Date(job.submitted_at).toLocaleString()}
            {job.items_processed !== undefined &&
              ` • ${job.items_processed} items`}
            {job.bytes_freed !== undefined &&
              ` • ${formatBytes(job.bytes_freed)} freed`}
          </div>
        </Link>
      ))}
    </div>
  );
}

// Main Wizard Component
export function DataCleanupWizardPage() {
  const [step, setStep] = useState<WizardStep>("filters");
  const [filters, setFilters] = useState<FilterFormState>(defaultFilters);
  const [auditNote, setAuditNote] = useState("");
  const [submittedJob, setSubmittedJob] = useState<CleanupJob | null>(null);

  // Extract cleanup filters (without action)
  const cleanupFilters: CleanupFilters = useMemo(() => {
    const { action: _action, ...rest } = filters;
    return rest;
  }, [filters]);

  // Dry-run query (only when on preview step)
  const {
    data: dryRun,
    isLoading: isDryRunLoading,
    error: dryRunError,
  } = useCleanupDryRun(step === "preview" ? cleanupFilters : null);

  // Submit mutation
  const submitMutation = useSubmitCleanup();

  const handleSubmit = useCallback(async () => {
    try {
      const job = await submitMutation.mutateAsync({
        filters: cleanupFilters,
        action: filters.action,
        audit_note: auditNote,
      });
      setSubmittedJob(job);
      setStep("complete");
    } catch {
      // Error handled by mutation
    }
  }, [submitMutation, cleanupFilters, filters.action, auditNote]);

  const handleStartOver = useCallback(() => {
    setStep("filters");
    setFilters(defaultFilters);
    setAuditNote("");
    setSubmittedJob(null);
  }, []);

  // Step indicator
  const steps = [
    { id: "filters", label: "Select Scope" },
    { id: "preview", label: "Preview Impact" },
    { id: "confirm", label: "Confirm" },
    { id: "complete", label: "Complete" },
  ];

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-4xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Data Cleanup Wizard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Safely archive or delete data with audit trail
          </p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main wizard panel */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
              {/* Step indicator */}
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  {steps.map((s, i) => (
                    <React.Fragment key={s.id}>
                      <div className="flex items-center">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                            s.id === step
                              ? "bg-blue-600 text-white"
                              : steps.findIndex((x) => x.id === step) > i
                              ? "bg-green-500 text-white"
                              : "bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                          }`}
                        >
                          {steps.findIndex((x) => x.id === step) > i
                            ? "✓"
                            : i + 1}
                        </div>
                        <span className="ml-2 text-sm text-gray-600 dark:text-gray-400 hidden sm:inline">
                          {s.label}
                        </span>
                      </div>
                      {i < steps.length - 1 && (
                        <div className="flex-1 h-0.5 bg-gray-200 dark:bg-gray-700 mx-2" />
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* Step content */}
              <div className="p-6">
                {step === "filters" && (
                  <FilterStep
                    filters={filters}
                    onChange={setFilters}
                    onNext={() => setStep("preview")}
                  />
                )}
                {step === "preview" && (
                  <PreviewStep
                    filters={filters}
                    dryRun={dryRun}
                    isLoading={isDryRunLoading}
                    error={dryRunError}
                    onBack={() => setStep("filters")}
                    onNext={() => setStep("confirm")}
                  />
                )}
                {step === "confirm" && dryRun && (
                  <ConfirmStep
                    filters={filters}
                    dryRun={dryRun}
                    auditNote={auditNote}
                    onAuditNoteChange={setAuditNote}
                    onBack={() => setStep("preview")}
                    onSubmit={handleSubmit}
                    isSubmitting={submitMutation.isPending}
                  />
                )}
                {step === "complete" && submittedJob && (
                  <CompleteStep
                    job={submittedJob}
                    onStartOver={handleStartOver}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Sidebar: History */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Recent Cleanups
              </h3>
              <CleanupHistoryPanel />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default DataCleanupWizardPage;
