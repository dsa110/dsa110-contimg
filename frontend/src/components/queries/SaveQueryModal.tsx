/**
 * Save Query Modal Component
 *
 * Modal dialog for saving the current filter state as a named query.
 * Supports name, description, visibility settings, and context.
 */

import React, { useState, useEffect } from "react";
import type { UrlFilterState } from "../../hooks/useUrlFilterState";
import {
  useCreateSavedQuery,
  useUpdateSavedQuery,
  type SavedQuery,
  type QueryVisibility,
  type QueryContext,
  getFilterSummary,
} from "../../api/savedQueries";

export interface SaveQueryModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Current filter state to save */
  filters: UrlFilterState;
  /** Context for the query (where it's being saved from) */
  context: QueryContext;
  /** Existing query to update (if editing) */
  existingQuery?: SavedQuery;
  /** Success callback with the saved query */
  onSuccess?: (query: SavedQuery) => void;
}

const VISIBILITY_OPTIONS: {
  value: QueryVisibility;
  label: string;
  desc: string;
}[] = [
  {
    value: "private",
    label: "🔒 Private",
    desc: "Only you can see this query",
  },
  {
    value: "shared",
    label: "👥 Shared",
    desc: "Team members can see and use this query",
  },
  {
    value: "global",
    label: "🌐 Public",
    desc: "Anyone can see and use this query",
  },
];

export function SaveQueryModal({
  isOpen,
  onClose,
  filters,
  context,
  existingQuery,
  onSuccess,
}: SaveQueryModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<QueryVisibility>("private");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useCreateSavedQuery();
  const updateMutation = useUpdateSavedQuery();

  const isEditing = Boolean(existingQuery);
  const isPending = createMutation.isPending || updateMutation.isPending;

  // Initialize form when editing
  useEffect(() => {
    if (existingQuery) {
      setName(existingQuery.name);
      setDescription(existingQuery.description ?? "");
      setVisibility(existingQuery.visibility);
    } else {
      setName("");
      setDescription("");
      setVisibility("private");
    }
    setError(null);
  }, [existingQuery, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Name is required");
      return;
    }

    try {
      let result: SavedQuery;

      if (isEditing && existingQuery) {
        result = await updateMutation.mutateAsync({
          id: existingQuery.id,
          data: {
            name: trimmedName,
            description: description.trim() || undefined,
            visibility,
            filters,
          },
        });
      } else {
        result = await createMutation.mutateAsync({
          name: trimmedName,
          description: description.trim() || undefined,
          visibility,
          context,
          filters,
        });
      }

      onSuccess?.(result);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save query");
    }
  };

  if (!isOpen) return null;

  const filterSummary = getFilterSummary(filters);
  const hasFilters = Object.values(filters).some((v) => v !== undefined);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-md transform bg-white dark:bg-gray-800 rounded-lg shadow-xl transition-all">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {isEditing ? "Edit Saved Query" : "Save Query"}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
              aria-label="Close"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
            {/* Filter Summary */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                Filters to Save
              </div>
              <div className="text-sm text-gray-700 dark:text-gray-300">
                {hasFilters ? (
                  filterSummary
                ) : (
                  <span className="text-amber-600 dark:text-amber-400">
                    ⚠️ No filters active - save anyway?
                  </span>
                )}
              </div>
            </div>

            {/* Name */}
            <div>
              <label
                htmlFor="query-name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Name <span className="text-red-500">*</span>
              </label>
              <input
                id="query-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Bright sources near M31"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                         placeholder:text-gray-400 dark:placeholder:text-gray-500"
                autoFocus
                maxLength={100}
                disabled={isPending}
              />
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="query-description"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Description (optional)
              </label>
              <textarea
                id="query-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add notes about this query..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                         placeholder:text-gray-400 dark:placeholder:text-gray-500 resize-none"
                maxLength={500}
                disabled={isPending}
              />
            </div>

            {/* Visibility */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Visibility
              </label>
              <div className="space-y-2">
                {VISIBILITY_OPTIONS.map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex items-start p-3 rounded-lg border cursor-pointer transition-colors ${
                      visibility === opt.value
                        ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                        : "border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="visibility"
                      value={opt.value}
                      checked={visibility === opt.value}
                      onChange={(e) =>
                        setVisibility(e.target.value as QueryVisibility)
                      }
                      className="sr-only"
                      disabled={isPending}
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {opt.label}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {opt.desc}
                      </div>
                    </div>
                    {visibility === opt.value && (
                      <svg
                        className="w-5 h-5 text-blue-500"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </label>
                ))}
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-3">
                <p className="text-sm text-red-700 dark:text-red-300">
                  {error}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isPending}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300
                         bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                         rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600
                         disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="px-4 py-2 text-sm font-medium text-white
                         bg-blue-600 hover:bg-blue-700 rounded-lg
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors flex items-center gap-2"
              >
                {isPending ? (
                  <>
                    <svg
                      className="w-4 h-4 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Saving...
                  </>
                ) : (
                  <>
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
                        d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
                      />
                    </svg>
                    {isEditing ? "Update Query" : "Save Query"}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default SaveQueryModal;
