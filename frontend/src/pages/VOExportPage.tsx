/**
 * VO Export Page
 *
 * Provides UI for exporting data in Virtual Observatory formats:
 * - Create exports in VOTable, FITS, CSV, JSON
 * - Cone search interface
 * - Column selection
 * - Export history
 */

import React, { useState, useMemo } from "react";
import {
  useExportJobs,
  useCreateExport,
  useDeleteExport,
  useExportPreview,
  useConeSearch,
  type ExportJob,
  type VOFormat,
  type ExportDataType,
  type ExportFilter,
  type ConeSearchResult,
  formatVOFormat,
  formatDataType,
  formatFileSize,
} from "../api/vo-export";

// ============================================================================
// Sub-components
// ============================================================================

interface ConeSearchPanelProps {
  onSearch: (result: ConeSearchResult) => void;
}

function ConeSearchPanel({ onSearch }: ConeSearchPanelProps) {
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [radius, setRadius] = useState("5");

  const coneSearch = useConeSearch();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await coneSearch.mutateAsync({
      ra: parseFloat(ra),
      dec: parseFloat(dec),
      radius_arcmin: parseFloat(radius),
      limit: 100,
    });
    onSearch(result);
  };

  const isValid =
    ra && dec && radius && !isNaN(parseFloat(ra)) && !isNaN(parseFloat(dec));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Cone Search
      </h3>
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label
              htmlFor="cone-ra"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              RA (deg)
            </label>
            <input
              id="cone-ra"
              type="number"
              step="any"
              value={ra}
              onChange={(e) => setRa(e.target.value)}
              placeholder="180.0"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label
              htmlFor="cone-dec"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Dec (deg)
            </label>
            <input
              id="cone-dec"
              type="number"
              step="any"
              value={dec}
              onChange={(e) => setDec(e.target.value)}
              placeholder="-30.0"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label
              htmlFor="cone-radius"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Radius (arcmin)
            </label>
            <input
              id="cone-radius"
              type="number"
              step="any"
              min="0.1"
              max="60"
              value={radius}
              onChange={(e) => setRadius(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={!isValid || coneSearch.isPending}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {coneSearch.isPending ? (
            <>
              <span className="animate-spin">⏳</span>
              Searching...
            </>
          ) : (
            <>
              <span>🔍</span>
              Search
            </>
          )}
        </button>
      </form>

      {coneSearch.data && (
        <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            Found {coneSearch.data.total_matches} sources
          </div>
          {coneSearch.data.sources.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
              {coneSearch.data.sources.slice(0, 5).map((source) => (
                <li key={source.id}>
                  {source.name} - {source.separation_arcsec.toFixed(1)}&quot;
                </li>
              ))}
              {coneSearch.data.sources.length > 5 && (
                <li className="text-gray-400">
                  ...and {coneSearch.data.sources.length - 5} more
                </li>
              )}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

interface CreateExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialFilter?: Partial<ExportFilter>;
}

function CreateExportModal({
  isOpen,
  onClose,
  initialFilter,
}: CreateExportModalProps) {
  const [name, setName] = useState("");
  const [format, setFormat] = useState<VOFormat>("votable");
  const [dataType, setDataType] = useState<ExportDataType>(
    initialFilter?.data_type ?? "sources"
  );
  const [useConeSearch, setUseConeSearch] = useState(
    !!initialFilter?.cone_search
  );
  const [ra, setRa] = useState(
    initialFilter?.cone_search?.ra?.toString() ?? ""
  );
  const [dec, setDec] = useState(
    initialFilter?.cone_search?.dec?.toString() ?? ""
  );
  const [radius, setRadius] = useState(
    initialFilter?.cone_search?.radius_arcmin?.toString() ?? "10"
  );
  const [limit, setLimit] = useState("10000");

  const createExport = useCreateExport();
  const previewMutation = useExportPreview();

  const filter: ExportFilter = useMemo(() => {
    const f: ExportFilter = {
      data_type: dataType,
      limit: parseInt(limit) || undefined,
    };
    if (useConeSearch && ra && dec && radius) {
      f.cone_search = {
        ra: parseFloat(ra),
        dec: parseFloat(dec),
        radius_arcmin: parseFloat(radius),
      };
    }
    return f;
  }, [dataType, useConeSearch, ra, dec, radius, limit]);

  const handlePreview = async () => {
    await previewMutation.mutateAsync(filter);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createExport.mutateAsync({
        name: name || `${formatDataType(dataType)} Export`,
        format,
        filter,
      });
      onClose();
      // Reset form
      setName("");
      setFormat("votable");
      setDataType("sources");
      setUseConeSearch(false);
    } catch {
      // Error handled by mutation
    }
  };

  if (!isOpen) return null;

  const preview = previewMutation.data;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div
          className="fixed inset-0 bg-black/50 transition-opacity"
          onClick={onClose}
        />
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Create VO Export
              </h2>
            </div>

            <div className="p-6 space-y-6">
              {/* Export Name */}
              <div>
                <label
                  htmlFor="export-name"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Export Name
                </label>
                <input
                  id="export-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={`${formatDataType(dataType)} Export`}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Format Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Export Format
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {(["votable", "fits", "csv", "json"] as VOFormat[]).map(
                    (f) => (
                      <label
                        key={f}
                        className={`flex items-center justify-center p-3 rounded-lg border cursor-pointer transition-colors ${
                          format === f
                            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                            : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                        }`}
                      >
                        <input
                          type="radio"
                          name="format"
                          value={f}
                          checked={format === f}
                          onChange={() => setFormat(f)}
                          className="sr-only"
                        />
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {formatVOFormat(f)}
                        </span>
                      </label>
                    )
                  )}
                </div>
              </div>

              {/* Data Type Selection */}
              <div>
                <label
                  htmlFor="data-type"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Data Type
                </label>
                <select
                  id="data-type"
                  value={dataType}
                  onChange={(e) =>
                    setDataType(e.target.value as ExportDataType)
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="sources">Sources</option>
                  <option value="images">Images</option>
                  <option value="catalogs">Catalogs</option>
                  <option value="spectra">Spectra</option>
                </select>
              </div>

              {/* Cone Search Toggle */}
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={useConeSearch}
                  onChange={(e) => setUseConeSearch(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-gray-700 dark:text-gray-300">
                  Apply cone search filter
                </span>
              </label>

              {/* Cone Search Parameters */}
              {useConeSearch && (
                <div className="grid grid-cols-3 gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div>
                    <label
                      htmlFor="export-ra"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                      RA (deg)
                    </label>
                    <input
                      id="export-ra"
                      type="number"
                      step="any"
                      value={ra}
                      onChange={(e) => setRa(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="export-dec"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                      Dec (deg)
                    </label>
                    <input
                      id="export-dec"
                      type="number"
                      step="any"
                      value={dec}
                      onChange={(e) => setDec(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="export-radius"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                      Radius (arcmin)
                    </label>
                    <input
                      id="export-radius"
                      type="number"
                      step="any"
                      value={radius}
                      onChange={(e) => setRadius(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                </div>
              )}

              {/* Record Limit */}
              <div>
                <label
                  htmlFor="export-limit"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Max Records
                </label>
                <input
                  id="export-limit"
                  type="number"
                  min="1"
                  max="1000000"
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Preview Button */}
              <button
                type="button"
                onClick={handlePreview}
                disabled={previewMutation.isPending}
                className="w-full px-4 py-2 border border-blue-500 text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {previewMutation.isPending ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Estimating...
                  </>
                ) : (
                  <>
                    <span>📊</span>
                    Preview Export
                  </>
                )}
              </button>

              {/* Preview Results */}
              {preview && (
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                    Export Preview
                  </h4>
                  <dl className="grid grid-cols-2 gap-2 text-sm">
                    <dt className="text-gray-500 dark:text-gray-400">
                      Estimated records:
                    </dt>
                    <dd className="text-gray-900 dark:text-gray-100">
                      {preview.estimated_records.toLocaleString()}
                    </dd>
                    <dt className="text-gray-500 dark:text-gray-400">
                      Estimated size:
                    </dt>
                    <dd className="text-gray-900 dark:text-gray-100">
                      {formatFileSize(preview.estimated_size_bytes)}
                    </dd>
                    <dt className="text-gray-500 dark:text-gray-400">
                      Estimated time:
                    </dt>
                    <dd className="text-gray-900 dark:text-gray-100">
                      ~{Math.ceil(preview.estimated_time_seconds / 60)} min
                    </dd>
                  </dl>
                  {preview.warnings.length > 0 && (
                    <div className="mt-2 text-sm text-yellow-600 dark:text-yellow-400">
                      {preview.warnings.map((w: string, i: number) => (
                        <div key={i}>⚠️ {w}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {createExport.isError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
                  Export failed:{" "}
                  {(createExport.error as Error)?.message || "Unknown error"}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createExport.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {createExport.isPending ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Creating...
                  </>
                ) : (
                  <>
                    <span>📤</span>
                    Create Export
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

interface ExportJobCardProps {
  job: ExportJob;
  onDelete: (id: string) => void;
}

function ExportJobCard({ job, onDelete }: ExportJobCardProps) {
  const statusColors: Record<string, string> = {
    pending: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30",
    processing: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
    completed: "text-green-600 bg-green-100 dark:bg-green-900/30",
    failed: "text-red-600 bg-red-100 dark:bg-red-900/30",
    expired: "text-gray-600 bg-gray-100 dark:bg-gray-700",
  };

  const formatIcons: Record<VOFormat, string> = {
    votable: "📋",
    fits: "🔭",
    csv: "📊",
    json: "{ }",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">{formatIcons[job.format]}</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {job.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {formatVOFormat(job.format)} • {formatDataType(job.data_type)}
            </p>
          </div>
        </div>
        <span
          className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${
            statusColors[job.status]
          }`}
        >
          {job.status}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-gray-500 dark:text-gray-400">Records</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {job.record_count.toLocaleString()}
          </div>
        </div>
        <div>
          <div className="text-gray-500 dark:text-gray-400">Size</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {job.file_size_formatted}
          </div>
        </div>
        <div>
          <div className="text-gray-500 dark:text-gray-400">Created</div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {new Date(job.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      {job.filter.cone_search && (
        <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          📍 Cone search: {job.filter.cone_search.ra.toFixed(4)}°,{" "}
          {job.filter.cone_search.dec.toFixed(4)}° (r=
          {job.filter.cone_search.radius_arcmin}&apos;)
        </div>
      )}

      {job.error_message && (
        <div className="mt-3 text-sm text-red-600 dark:text-red-400">
          ⚠️ {job.error_message}
        </div>
      )}

      <div className="mt-4 flex gap-2">
        {job.status === "completed" && job.download_url && (
          <a
            href={job.download_url}
            download
            className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"
          >
            <span>⬇️</span>
            Download
          </a>
        )}
        {(job.status === "pending" || job.status === "processing") && (
          <button
            onClick={() => onDelete(job.id)}
            className="px-3 py-1.5 text-sm border border-yellow-300 text-yellow-600 rounded hover:bg-yellow-50 dark:hover:bg-yellow-900/20 flex items-center gap-1"
          >
            <span>⏹️</span>
            Cancel
          </button>
        )}
        {(job.status === "completed" ||
          job.status === "failed" ||
          job.status === "expired") && (
          <button
            onClick={() => onDelete(job.id)}
            className="px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-1"
          >
            <span>🗑️</span>
            Delete
          </button>
        )}
      </div>
    </div>
  );
}

function ExportStatsPanel({ jobs }: { jobs: ExportJob[] }) {
  const stats = useMemo(() => {
    const completed = jobs.filter((j) => j.status === "completed");
    const totalSize = completed.reduce((sum, j) => sum + j.file_size_bytes, 0);
    const totalRecords = completed.reduce((sum, j) => sum + j.record_count, 0);

    return {
      total: jobs.length,
      completed: completed.length,
      pending: jobs.filter(
        (j) => j.status === "pending" || j.status === "processing"
      ).length,
      failed: jobs.filter((j) => j.status === "failed").length,
      totalSize,
      totalRecords,
    };
  }, [jobs]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Export Statistics
      </h3>
      <dl className="space-y-3 text-sm">
        <div className="flex justify-between">
          <dt className="text-gray-500 dark:text-gray-400">Total Exports</dt>
          <dd className="font-medium text-gray-900 dark:text-gray-100">
            {stats.total}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500 dark:text-gray-400">Completed</dt>
          <dd className="font-medium text-green-600">{stats.completed}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500 dark:text-gray-400">In Progress</dt>
          <dd className="font-medium text-blue-600">{stats.pending}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500 dark:text-gray-400">Failed</dt>
          <dd className="font-medium text-red-600">{stats.failed}</dd>
        </div>
        <div className="border-t border-gray-200 dark:border-gray-700 pt-3 flex justify-between">
          <dt className="text-gray-500 dark:text-gray-400">Total Size</dt>
          <dd className="font-medium text-gray-900 dark:text-gray-100">
            {formatFileSize(stats.totalSize)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500 dark:text-gray-400">Total Records</dt>
          <dd className="font-medium text-gray-900 dark:text-gray-100">
            {stats.totalRecords.toLocaleString()}
          </dd>
        </div>
      </dl>
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

export function VOExportPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formatFilter, setFormatFilter] = useState<VOFormat | "all">("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [, setConeSearchResult] = useState<ConeSearchResult | null>(null);

  const { data: jobs, isLoading, error } = useExportJobs({ limit: 50 });
  const deleteExport = useDeleteExport();

  const filteredJobs = useMemo(() => {
    if (!jobs) return [];
    return jobs.filter((job: ExportJob) => {
      if (formatFilter !== "all" && job.format !== formatFilter) return false;
      if (statusFilter !== "all" && job.status !== statusFilter) return false;
      return true;
    });
  }, [jobs, formatFilter, statusFilter]);

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this export?")) {
      await deleteExport.mutateAsync(id);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                VO Export
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Export data in Virtual Observatory formats
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <span>📤</span>
              New Export
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Export List */}
          <div className="lg:col-span-2 space-y-4">
            {/* Filters */}
            <div className="flex gap-4">
              <select
                value={formatFilter}
                onChange={(e) =>
                  setFormatFilter(e.target.value as VOFormat | "all")
                }
                aria-label="Filter by format"
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              >
                <option value="all">All Formats</option>
                <option value="votable">VOTable</option>
                <option value="fits">FITS</option>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter by status"
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Export History
            </h2>

            {isLoading && (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse"
                  />
                ))}
              </div>
            )}

            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                Failed to load exports: {(error as Error)?.message}
              </div>
            )}

            {filteredJobs.length === 0 && !isLoading && (
              <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
                <div className="text-6xl mb-4">📤</div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  No Exports Yet
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mt-1">
                  Create your first VO export
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  New Export
                </button>
              </div>
            )}

            {filteredJobs.length > 0 && (
              <div className="space-y-4">
                {filteredJobs.map((job: ExportJob) => (
                  <ExportJobCard
                    key={job.id}
                    job={job}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Cone Search */}
            <ConeSearchPanel onSearch={setConeSearchResult} />

            {/* Stats */}
            {jobs && jobs.length > 0 && <ExportStatsPanel jobs={jobs} />}

            {/* Format Info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Supported Formats
              </h3>
              <ul className="space-y-3 text-sm">
                <li className="flex items-start gap-2">
                  <span>📋</span>
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      VOTable
                    </div>
                    <div className="text-gray-500 dark:text-gray-400">
                      IVOA standard XML format
                    </div>
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <span>🔭</span>
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      FITS
                    </div>
                    <div className="text-gray-500 dark:text-gray-400">
                      Binary table format with WCS
                    </div>
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <span>📊</span>
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      CSV
                    </div>
                    <div className="text-gray-500 dark:text-gray-400">
                      Comma-separated values
                    </div>
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <span>{"{ }"}</span>
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      JSON
                    </div>
                    <div className="text-gray-500 dark:text-gray-400">
                      JavaScript Object Notation
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      <CreateExportModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </div>
  );
}

export default VOExportPage;
