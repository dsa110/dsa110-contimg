/**
 * Shared Queries Page
 *
 * Dashboard for creating, managing, and executing saved database queries
 * that can be shared with team members.
 */

import React, { useState, useMemo } from "react";
import {
  useQueries,
  useQueryStats,
  useCreateQuery,
  useDeleteQuery,
  useRunQuery,
  useFavoriteQuery,
  useUnfavoriteQuery,
  useCloneQuery,
  getTargetTypeLabel,
  getVisibilityIcon,
  getVisibilityLabel,
  formatExecutionTime,
  validateQuerySyntax,
  extractParameters,
  type SavedQuery,
  type QueryTarget,
  type QueryVisibility,
  type QueryResult,
  type QuerySearchParams,
} from "../api/queries";

// ============================================================================
// Types
// ============================================================================

type TabType = "all" | "mine" | "favorites" | "team" | "public";

// ============================================================================
// Sub-Components
// ============================================================================

interface QueryCardProps {
  query: SavedQuery;
  isOwner: boolean;
  onRun: (query: SavedQuery) => void;
  onFavorite: (id: string) => void;
  onUnfavorite: (id: string) => void;
  onClone: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (query: SavedQuery) => void;
}

function QueryCard({
  query,
  isOwner,
  onRun,
  onFavorite,
  onUnfavorite,
  onClone,
  onDelete,
  onEdit,
}: QueryCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {query.name}
            </h3>
            <span
              className="text-sm"
              title={getVisibilityLabel(query.visibility)}
            >
              {getVisibilityIcon(query.visibility)}
            </span>
            {query.is_favorite && (
              <span className="text-yellow-500" title="Favorite">
                ⭐
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {query.description || "No description"}
          </p>
        </div>
        <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
          {getTargetTypeLabel(query.target_type)}
        </span>
      </div>

      {/* Query Preview */}
      <div className="mt-3 bg-gray-50 dark:bg-gray-900 rounded p-2 font-mono text-xs text-gray-700 dark:text-gray-300 overflow-x-auto">
        <pre className="whitespace-pre-wrap break-words">
          {query.query_string.length > 200
            ? query.query_string.substring(0, 200) + "..."
            : query.query_string}
        </pre>
      </div>

      {/* Tags */}
      {query.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {query.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Metadata */}
      <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
        <span>by {query.owner_name}</span>
        <span>•</span>
        <span>{query.run_count} runs</span>
        {query.last_run_at && (
          <>
            <span>•</span>
            <span>
              Last run: {new Date(query.last_run_at).toLocaleDateString()}
            </span>
          </>
        )}
      </div>

      {/* Actions */}
      <div className="mt-4 flex items-center gap-2 border-t border-gray-200 dark:border-gray-700 pt-4">
        <button
          onClick={() => onRun(query)}
          className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          ▶ Run
        </button>
        {query.is_favorite ? (
          <button
            onClick={() => onUnfavorite(query.id)}
            className="px-3 py-1.5 text-sm text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded"
          >
            ★ Unfavorite
          </button>
        ) : (
          <button
            onClick={() => onFavorite(query.id)}
            className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            ☆ Favorite
          </button>
        )}
        <button
          onClick={() => onClone(query.id)}
          className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
        >
          📋 Clone
        </button>
        {isOwner && (
          <>
            <button
              onClick={() => onEdit(query)}
              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              ✏️ Edit
            </button>
            <button
              onClick={() => onDelete(query.id)}
              className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded ml-auto"
            >
              🗑️ Delete
            </button>
          </>
        )}
      </div>
    </div>
  );
}

interface CreateQueryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description: string;
    query_string: string;
    target_type: QueryTarget;
    visibility: QueryVisibility;
    tags: string[];
  }) => Promise<void>;
  editQuery?: SavedQuery | null;
  isPending: boolean;
}

function CreateQueryModal({
  isOpen,
  onClose,
  onSubmit,
  editQuery,
  isPending,
}: CreateQueryModalProps) {
  const [name, setName] = useState(editQuery?.name || "");
  const [description, setDescription] = useState(editQuery?.description || "");
  const [queryString, setQueryString] = useState(editQuery?.query_string || "");
  const [targetType, setTargetType] = useState<QueryTarget>(
    editQuery?.target_type || "source"
  );
  const [visibility, setVisibility] = useState<QueryVisibility>(
    editQuery?.visibility || "private"
  );
  const [tags, setTags] = useState(editQuery?.tags.join(", ") || "");
  const [syntaxError, setSyntaxError] = useState<string | null>(null);

  // Extract detected parameters
  const detectedParams = useMemo(
    () => extractParameters(queryString),
    [queryString]
  );

  const handleQueryChange = (value: string) => {
    setQueryString(value);
    const validation = validateQuerySyntax(value);
    setSyntaxError(validation.valid ? null : validation.error || null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validation = validateQuerySyntax(queryString);
    if (!validation.valid) {
      setSyntaxError(validation.error || "Invalid query");
      return;
    }

    await onSubmit({
      name,
      description,
      query_string: queryString,
      target_type: targetType,
      visibility,
      tags: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    });

    // Reset form
    setName("");
    setDescription("");
    setQueryString("");
    setTags("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {editQuery ? "Edit Query" : "New Query"}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label
              htmlFor="query-name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Name
            </label>
            <input
              id="query-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Find bright sources"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              required
            />
          </div>

          <div>
            <label
              htmlFor="query-description"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Description
            </label>
            <input
              id="query-description"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="query-target"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Target Type
              </label>
              <select
                id="query-target"
                value={targetType}
                onChange={(e) => setTargetType(e.target.value as QueryTarget)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="source">Sources</option>
                <option value="image">Images</option>
                <option value="job">Jobs</option>
                <option value="observation">Observations</option>
                <option value="ms">Measurement Sets</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="query-visibility"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Visibility
              </label>
              <select
                id="query-visibility"
                value={visibility}
                onChange={(e) =>
                  setVisibility(e.target.value as QueryVisibility)
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="private">🔒 Private</option>
                <option value="team">👥 Team</option>
                <option value="public">🌐 Public</option>
              </select>
            </div>
          </div>

          <div>
            <label
              htmlFor="query-string"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Query
            </label>
            <textarea
              id="query-string"
              value={queryString}
              onChange={(e) => handleQueryChange(e.target.value)}
              placeholder="SELECT * FROM sources WHERE flux > {{min_flux}}"
              rows={6}
              className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono text-sm ${
                syntaxError
                  ? "border-red-500"
                  : "border-gray-300 dark:border-gray-600"
              }`}
              required
            />
            {syntaxError && (
              <p className="text-red-500 text-sm mt-1">{syntaxError}</p>
            )}
            {detectedParams.length > 0 && (
              <p className="text-blue-600 text-sm mt-1">
                Detected parameters: {detectedParams.join(", ")}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="query-tags"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Tags (comma-separated)
            </label>
            <input
              id="query-tags"
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g., flux, calibration, daily"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || !name.trim() || !queryString.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending
                ? "Saving..."
                : editQuery
                ? "Update Query"
                : "Save Query"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface RunQueryModalProps {
  isOpen: boolean;
  onClose: () => void;
  query: SavedQuery | null;
  onRun: (queryId: string, params: Record<string, string>) => Promise<void>;
  result: QueryResult | null;
  isPending: boolean;
}

function RunQueryModal({
  isOpen,
  onClose,
  query,
  onRun,
  result,
  isPending,
}: RunQueryModalProps) {
  const [params, setParams] = useState<Record<string, string>>({});

  const detectedParams = useMemo(
    () => (query ? extractParameters(query.query_string) : []),
    [query]
  );

  const handleRun = async () => {
    if (query) {
      await onRun(query.id, params);
    }
  };

  if (!isOpen || !query) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Run Query: {query.name}
          </h2>
        </div>

        <div className="p-4 space-y-4">
          {/* Query Preview */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Query
            </h3>
            <pre className="bg-gray-50 dark:bg-gray-900 rounded p-3 font-mono text-sm text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap">
              {query.query_string}
            </pre>
          </div>

          {/* Parameters */}
          {detectedParams.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Parameters
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {detectedParams.map((param) => (
                  <div key={param}>
                    <label
                      htmlFor={`param-${param}`}
                      className="block text-sm text-gray-600 dark:text-gray-400 mb-1"
                    >
                      {param}
                    </label>
                    <input
                      id={`param-${param}`}
                      type="text"
                      value={params[param] || ""}
                      onChange={(e) =>
                        setParams((prev) => ({
                          ...prev,
                          [param]: e.target.value,
                        }))
                      }
                      placeholder={`Enter ${param}`}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {result && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Results ({result.row_count} rows)
                </h3>
                <span className="text-xs text-gray-500">
                  Executed in {formatExecutionTime(result.execution_time_ms)}
                  {result.truncated && " (truncated)"}
                </span>
              </div>
              <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      {result.columns.map((col) => (
                        <th
                          key={col}
                          className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {result.rows.map((row, idx) => (
                      <tr key={idx}>
                        {result.columns.map((col) => (
                          <td
                            key={col}
                            className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100 whitespace-nowrap"
                          >
                            {String(row[col] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Close
            </button>
            <button
              onClick={handleRun}
              disabled={isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isPending ? "Running..." : "▶ Run Query"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatsPanel({
  stats,
}: {
  stats: import("../api/queries").QueryStats | undefined;
}) {
  if (!stats) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        📊 Query Statistics
      </h3>

      <div className="grid grid-cols-2 gap-4">
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.total_queries}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Total Queries
          </div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">
            {stats.public_queries}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Public</div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {stats.team_queries}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Team</div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-600">
            {stats.private_queries}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Private
          </div>
        </div>
      </div>

      {/* Activity */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">
            Queries Run Today
          </span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {stats.queries_run_today}
          </span>
        </div>
        <div className="flex justify-between text-sm mt-2">
          <span className="text-gray-500 dark:text-gray-400">This Week</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {stats.queries_run_this_week}
          </span>
        </div>
      </div>
    </div>
  );
}

function TopQueriesPanel({
  queries,
}: {
  queries: Array<{
    id: string;
    name: string;
    run_count: number;
    owner_name: string;
  }>;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        🔥 Popular Queries
      </h3>

      <div className="space-y-3">
        {queries.map((query, index) => (
          <div key={query.id} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-gray-500 dark:text-gray-400 font-medium">
                #{index + 1}
              </span>
              <div>
                <span className="text-gray-900 dark:text-gray-100 text-sm">
                  {query.name}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                  by {query.owner_name}
                </span>
              </div>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {query.run_count} runs
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PopularTagsPanel({
  tags,
}: {
  tags: Array<{ tag: string; count: number }>;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        🏷️ Popular Tags
      </h3>

      <div className="flex flex-wrap gap-2">
        {tags.map(({ tag, count }) => (
          <span
            key={tag}
            className="px-3 py-1 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full"
          >
            {tag} ({count})
          </span>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function SharedQueriesPage() {
  const [activeTab, setActiveTab] = useState<TabType>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterTarget, setFilterTarget] = useState<QueryTarget | "">("");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editQuery, setEditQuery] = useState<SavedQuery | null>(null);
  const [runQuery, setRunQuery] = useState<SavedQuery | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);

  // Build search params based on active tab and filters
  const searchParams: QuerySearchParams = useMemo(() => {
    const params: QuerySearchParams = {
      sort_by: "updated_at",
      sort_order: "desc",
    };

    if (searchTerm) {
      params.search = searchTerm;
    }

    if (filterTarget) {
      params.target_type = filterTarget;
    }

    switch (activeTab) {
      case "mine":
        params.owner_id = "me";
        break;
      case "favorites":
        params.is_favorite = true;
        break;
      case "team":
        params.visibility = "team";
        break;
      case "public":
        params.visibility = "public";
        break;
    }

    return params;
  }, [activeTab, searchTerm, filterTarget]);

  // Queries
  const {
    data: queries,
    isPending: isLoadingQueries,
    error: queriesError,
  } = useQueries(searchParams);
  const { data: stats } = useQueryStats();

  // Mutations
  const createQuery = useCreateQuery();
  const deleteQuery = useDeleteQuery();
  const runQueryMutation = useRunQuery();
  const favoriteQuery = useFavoriteQuery();
  const unfavoriteQuery = useUnfavoriteQuery();
  const cloneQuery = useCloneQuery();

  // Handlers
  const handleCreateQuery = async (data: {
    name: string;
    description: string;
    query_string: string;
    target_type: QueryTarget;
    visibility: QueryVisibility;
    tags: string[];
  }) => {
    await createQuery.mutateAsync(data);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this query?")) {
      await deleteQuery.mutateAsync(id);
    }
  };

  const handleRunQuery = async (
    queryId: string,
    params: Record<string, string>
  ) => {
    const result = await runQueryMutation.mutateAsync({
      query_id: queryId,
      parameters: params,
    });
    setQueryResult(result);
  };

  const handleOpenRun = (query: SavedQuery) => {
    setRunQuery(query);
    setQueryResult(null);
  };

  const handleEdit = (query: SavedQuery) => {
    setEditQuery(query);
    setIsCreateModalOpen(true);
  };

  const handleOpenCreate = () => {
    setEditQuery(null);
    setIsCreateModalOpen(true);
  };

  const tabs: Array<{ key: TabType; label: string; count?: number }> = [
    { key: "all", label: "All Queries", count: stats?.total_queries },
    { key: "mine", label: "My Queries" },
    { key: "favorites", label: "⭐ Favorites" },
    { key: "team", label: "👥 Team", count: stats?.team_queries },
    { key: "public", label: "🌐 Public", count: stats?.public_queries },
  ];

  // Current user ID (would come from auth context in real app)
  const currentUserId = "me";

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            📝 Shared Queries
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Save, share, and run database queries
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <span>+</span>
          New Query
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3 space-y-4">
          {/* Tabs */}
          <div className="flex items-center gap-2 border-b border-gray-200 dark:border-gray-700">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                }`}
              >
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-2 text-xs bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Search queries..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <select
              value={filterTarget}
              onChange={(e) =>
                setFilterTarget(e.target.value as QueryTarget | "")
              }
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              aria-label="Filter by target type"
            >
              <option value="">All Targets</option>
              <option value="source">Sources</option>
              <option value="image">Images</option>
              <option value="job">Jobs</option>
              <option value="observation">Observations</option>
              <option value="ms">Measurement Sets</option>
            </select>
          </div>

          {/* Queries List */}
          {isLoadingQueries ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              Loading queries...
            </div>
          ) : queriesError ? (
            <div className="text-center py-8 text-red-500">
              Error loading queries
            </div>
          ) : queries?.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              {activeTab === "mine"
                ? "You haven't created any queries yet."
                : activeTab === "favorites"
                ? "No favorite queries."
                : "No queries found."}
            </div>
          ) : (
            <div className="space-y-4">
              {queries?.map((query) => (
                <QueryCard
                  key={query.id}
                  query={query}
                  isOwner={query.owner_id === currentUserId}
                  onRun={handleOpenRun}
                  onFavorite={(id) => favoriteQuery.mutate(id)}
                  onUnfavorite={(id) => unfavoriteQuery.mutate(id)}
                  onClone={(id) => cloneQuery.mutate(id)}
                  onDelete={handleDelete}
                  onEdit={handleEdit}
                />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <StatsPanel stats={stats} />
          {stats?.top_queries && (
            <TopQueriesPanel queries={stats.top_queries} />
          )}
          {stats?.popular_tags && (
            <PopularTagsPanel tags={stats.popular_tags} />
          )}

          {/* Tips */}
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
              💡 Query Tips
            </h4>
            <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
              <li>• Use {"{{param}}"} for parameterized queries</li>
              <li>• Share team queries for collaboration</li>
              <li>• Clone queries to modify without changing original</li>
              <li>• Add tags for easy organization</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Create/Edit Query Modal */}
      <CreateQueryModal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setEditQuery(null);
        }}
        onSubmit={handleCreateQuery}
        editQuery={editQuery}
        isPending={createQuery.isPending}
      />

      {/* Run Query Modal */}
      <RunQueryModal
        isOpen={runQuery !== null}
        onClose={() => {
          setRunQuery(null);
          setQueryResult(null);
        }}
        query={runQuery}
        onRun={handleRunQuery}
        result={queryResult}
        isPending={runQueryMutation.isPending}
      />
    </div>
  );
}
