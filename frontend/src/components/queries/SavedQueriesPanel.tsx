/**
 * Saved Queries Panel Component
 *
 * Displays a list of saved queries with filtering, search, and actions.
 * Users can apply, edit, delete, and share saved queries.
 */

import React, { useState, useCallback } from "react";
import {
  useSavedQueries,
  useDeleteSavedQuery,
  useRecordQueryUsage,
  type SavedQuery,
  type SavedQueryFilters,
  type QueryContext,
  type QueryVisibility,
  getFilterSummary,
  getVisibilityIcon,
  getVisibilityLabel,
  generateShareableUrl,
} from "../../api/savedQueries";
import type { UrlFilterState } from "../../hooks/useUrlFilterState";

export interface SavedQueriesPanelProps {
  /** Current context to filter queries by (optional) */
  context?: QueryContext;
  /** Callback when a query is applied */
  onApply: (filters: UrlFilterState) => void;
  /** Callback when edit is requested */
  onEdit?: (query: SavedQuery) => void;
  /** Additional CSS classes */
  className?: string;
  /** Compact mode for sidebar display */
  compact?: boolean;
}

type OwnerFilter = "all" | "me" | "others";

export function SavedQueriesPanel({
  context,
  onApply,
  onEdit,
  className = "",
  compact = false,
}: SavedQueriesPanelProps) {
  const [search, setSearch] = useState("");
  const [ownerFilter, setOwnerFilter] = useState<OwnerFilter>("all");
  const [visibilityFilter, setVisibilityFilter] = useState<
    QueryVisibility | ""
  >("");
  const [page, setPage] = useState(1);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Build filter object
  const filters: SavedQueryFilters = {
    context,
    owner: ownerFilter === "all" ? undefined : ownerFilter,
    visibility: visibilityFilter || undefined,
    search: search.trim() || undefined,
  };

  const { data, isLoading, error, refetch } = useSavedQueries(filters, page);
  const deleteMutation = useDeleteSavedQuery();
  const recordUsageMutation = useRecordQueryUsage();

  const handleApply = useCallback(
    (query: SavedQuery) => {
      recordUsageMutation.mutate(query.id);
      onApply(query.filters);
    },
    [onApply, recordUsageMutation]
  );

  const handleDelete = useCallback(
    async (query: SavedQuery) => {
      if (!window.confirm(`Delete "${query.name}"? This cannot be undone.`)) {
        return;
      }
      try {
        await deleteMutation.mutateAsync(query.id);
      } catch {
        alert("Failed to delete query");
      }
    },
    [deleteMutation]
  );

  const handleCopyLink = useCallback(async (query: SavedQuery) => {
    const url = generateShareableUrl(query);
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(query.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback for browsers without clipboard API
      prompt("Copy this link:", url);
    }
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className={`${className} animate-pulse`}>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"
            />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={`${className} bg-red-50 dark:bg-red-900/30 rounded-lg p-4`}
      >
        <p className="text-red-700 dark:text-red-300 text-sm">
          Failed to load saved queries
        </p>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm text-red-600 hover:text-red-700 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const queries = data?.queries ?? [];
  const pagination = data?.pagination;
  const hasQueries = queries.length > 0;

  return (
    <div className={`${className} space-y-4`}>
      {/* Header & Filters */}
      {!compact && (
        <div className="flex flex-col gap-3">
          {/* Search */}
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search saved queries..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                       placeholder:text-gray-400 dark:placeholder:text-gray-500
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Filter Buttons */}
          <div className="flex flex-wrap gap-2">
            {/* Owner filter */}
            <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
              {(["all", "me", "others"] as OwnerFilter[]).map((opt) => (
                <button
                  key={opt}
                  onClick={() => {
                    setOwnerFilter(opt);
                    setPage(1);
                  }}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    ownerFilter === opt
                      ? "bg-blue-500 text-white"
                      : "bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600"
                  }`}
                >
                  {opt === "all" ? "All" : opt === "me" ? "Mine" : "Others"}
                </button>
              ))}
            </div>

            {/* Visibility filter */}
            <select
              value={visibilityFilter}
              onChange={(e) => {
                setVisibilityFilter(e.target.value as QueryVisibility | "");
                setPage(1);
              }}
              className="px-3 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded-lg
                       bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            >
              <option value="">All visibility</option>
              <option value="private">🔒 Private</option>
              <option value="shared">👥 Shared</option>
              <option value="global">🌐 Public</option>
            </select>
          </div>
        </div>
      )}

      {/* Compact search only */}
      {compact && (
        <div className="relative">
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search..."
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                     placeholder:text-gray-400 dark:placeholder:text-gray-500
                     focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      )}

      {/* Query List */}
      {!hasQueries ? (
        <div className="text-center py-8">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <p className="mt-2 text-gray-500 dark:text-gray-400">
            {search || ownerFilter !== "all" || visibilityFilter
              ? "No queries match your filters"
              : "No saved queries yet"}
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Save your current filters to quickly reuse them
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {queries.map((query) => (
            <QueryCard
              key={query.id}
              query={query}
              compact={compact}
              onApply={() => handleApply(query)}
              onEdit={onEdit ? () => onEdit(query) : undefined}
              onDelete={query.can_edit ? () => handleDelete(query) : undefined}
              onCopyLink={() => handleCopyLink(query)}
              isCopied={copiedId === query.id}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Page {pagination.page} of {pagination.total_pages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300
                       hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page >= pagination.total_pages}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300
                       hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// QueryCard Sub-component
// ============================================================================

interface QueryCardProps {
  query: SavedQuery;
  compact: boolean;
  onApply: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onCopyLink: () => void;
  isCopied: boolean;
}

function QueryCard({
  query,
  compact,
  onApply,
  onEdit,
  onDelete,
  onCopyLink,
  isCopied,
}: QueryCardProps) {
  const filterSummary = getFilterSummary(query.filters);

  if (compact) {
    return (
      <button
        onClick={onApply}
        className="w-full text-left p-2 rounded-lg border border-gray-200 dark:border-gray-700
                 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors group"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs">{getVisibilityIcon(query.visibility)}</span>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate flex-1">
            {query.name}
          </span>
          <span className="text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
            Apply →
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
          {filterSummary}
        </p>
      </button>
    );
  }

  return (
    <div className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="text-sm"
              title={getVisibilityLabel(query.visibility)}
            >
              {getVisibilityIcon(query.visibility)}
            </span>
            <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
              {query.name}
            </h3>
          </div>
          {query.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
              {query.description}
            </p>
          )}
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
            {filterSummary}
          </p>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400 dark:text-gray-500">
            <span>by {query.owner_username}</span>
            <span>•</span>
            <span>
              Used {query.use_count} time{query.use_count !== 1 ? "s" : ""}
            </span>
            <span>•</span>
            <span>{new Date(query.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        <button
          onClick={onApply}
          className="flex-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700
                   rounded-lg transition-colors"
        >
          Apply Filters
        </button>
        <button
          onClick={onCopyLink}
          title="Copy shareable link"
          className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300
                   rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          {isCopied ? (
            <svg
              className="w-5 h-5 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          ) : (
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
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          )}
        </button>
        {onEdit && (
          <button
            onClick={onEdit}
            title="Edit query"
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300
                     rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
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
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </button>
        )}
        {onDelete && (
          <button
            onClick={onDelete}
            title="Delete query"
            className="p-1.5 text-gray-500 hover:text-red-600 dark:hover:text-red-400
                     rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
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
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

export default SavedQueriesPanel;
