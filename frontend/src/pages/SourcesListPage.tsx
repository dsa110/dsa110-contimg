import React, { useState, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { useSources } from "../hooks/useQueries";
import { useUrlFilterState } from "../hooks/useUrlFilterState";
import { useSourceFiltering } from "../hooks/useSourceFiltering";
import { PageSkeleton, SortableTableHeader, useTableSort, Modal } from "../components/common";
import { AdvancedQueryPanel, SourceQueryParams } from "../components/query";
import { EtaVPlot, SourcePoint } from "../components/variability";
import {
  AdvancedFilterPanel,
  FilterDefinition,
  AdvancedFilterValues as FilterValues,
} from "../components/filters";
import { useSelectionStore } from "../stores/appStore";
import type { SourceSummary } from "../types";
import { ROUTES } from "../constants/routes";
import { config } from "../config";

/**
 * List page showing all detected sources with advanced query and variability plot.
 * Uses URL-based filter state for shareable/bookmarkable views.
 */
const SourcesListPage: React.FC = () => {
  const { data: sources, isLoading, error } = useSources();

  // URL-based filter state for shareable views
  const { filters, setFilters, clearFilters, hasActiveFilters } = useUrlFilterState();

  // Derive active tab from URL, default to "list"
  const activeTab = (filters.tab as "list" | "variability") || "list";
  const setActiveTab = useCallback(
    (tab: "list" | "variability") => setFilters({ tab }),
    [setFilters]
  );

  // Local UI state (not persisted in URL)
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);

  // Advanced filter definitions
  const advFilterDefs: FilterDefinition[] = [
    {
      id: "name",
      label: "Name Search",
      type: "text",
      group: "Basic",
      placeholder: "Search by name...",
    },
    {
      id: "minFlux",
      label: "Min Flux (Jy)",
      type: "range",
      group: "Flux",
      min: 0,
      max: 1,
      step: 0.001,
      unit: "Jy",
    },
    {
      id: "maxFlux",
      label: "Max Flux (Jy)",
      type: "range",
      group: "Flux",
      min: 0,
      max: 1,
      step: 0.001,
      unit: "Jy",
    },
    {
      id: "minImages",
      label: "Min Detections",
      type: "range",
      group: "Variability",
      min: 1,
      max: 100,
      step: 1,
    },
    { id: "variable", label: "Variable Only", type: "checkbox", group: "Variability" },
  ];

  // Multi-select state
  const selectedSources = useSelectionStore((s) => s.selectedSources);
  const toggleSourceSelection = useSelectionStore((s) => s.toggleSourceSelection);
  const selectAllSources = useSelectionStore((s) => s.selectAllSources);
  const clearSourceSelection = useSelectionStore((s) => s.clearSourceSelection);

  const selectedIds = useMemo(() => Array.from(selectedSources), [selectedSources]);

  const handleExportSelected = useCallback(() => {
    if (selectedIds.length === 0) return;
    setShowExportModal(true);
  }, [selectedIds]);

  const confirmExport = useCallback(() => {
    const baseUrl = config.api.baseUrl;
    window.open(`${baseUrl}/sources/export?ids=${selectedIds.join(",")}`, "_blank");
    setShowExportModal(false);
  }, [selectedIds]);

  // Use centralized filtering hook with URL state
  const { filteredSources, totalCount, filteredCount, isFiltered } = useSourceFiltering(
    sources as SourceSummary[] | undefined,
    {
      ra: filters.ra,
      dec: filters.dec,
      radius: filters.radius,
      minFlux: filters.minFlux,
      maxFlux: filters.maxFlux,
      name: filters.name,
      minImages: filters.minImages,
      variableOnly: filters.variable,
    }
  );

  // Adapter: Convert URL state to AdvancedFilterPanel values format
  const advFilterValues: FilterValues = useMemo(
    () => ({
      name: filters.name,
      minFlux: filters.minFlux,
      maxFlux: filters.maxFlux,
      minImages: filters.minImages,
      variable: filters.variable,
    }),
    [filters]
  );

  // Adapter: Handle AdvancedFilterPanel changes by updating URL state
  const handleAdvFilterChange = useCallback(
    (values: FilterValues) => {
      setFilters({
        name: values.name as string | undefined,
        minFlux: values.minFlux as number | undefined,
        maxFlux: values.maxFlux as number | undefined,
        minImages: values.minImages as number | undefined,
        variable: values.variable as boolean | undefined,
      });
    },
    [setFilters]
  );

  // Adapter: Handle AdvancedQueryPanel submit (cone search + flux)
  const handleQuerySubmit = useCallback(
    (params: SourceQueryParams) => {
      setFilters({
        ra: params.ra,
        dec: params.dec,
        radius: params.radius,
        // Extract simple min value from complex flux object
        minFlux: params.minFlux?.min,
        maxFlux: params.maxFlux?.max,
      });
    },
    [setFilters]
  );

  // Adapter: Convert URL state to AdvancedQueryPanel initialParams format
  const queryPanelInitialParams: Partial<SourceQueryParams> = useMemo(
    () => ({
      ra: filters.ra,
      dec: filters.dec,
      radius: filters.radius,
      minFlux:
        filters.minFlux !== undefined ? { min: filters.minFlux, type: "peak" as const } : undefined,
      maxFlux:
        filters.maxFlux !== undefined ? { max: filters.maxFlux, type: "peak" as const } : undefined,
    }),
    [filters.ra, filters.dec, filters.radius, filters.minFlux, filters.maxFlux]
  );

  const { sortColumn, sortDirection, handleSort, sortedData } = useTableSort<SourceSummary>(
    filteredSources,
    "id",
    "asc"
  );

  // Build EtaVPlot data from sources
  const variabilityData: SourcePoint[] = useMemo(() => {
    if (!sources) return [];
    return (sources as SourceSummary[])
      .filter(
        (s) =>
          s.eta !== undefined &&
          s.v !== undefined &&
          s.ra_deg !== undefined &&
          s.dec_deg !== undefined
      )
      .map((s) => ({
        id: s.id,
        name: s.name || s.id,
        ra: s.ra_deg!,
        dec: s.dec_deg!,
        eta: s.eta!,
        v: s.v!,
        peakFlux: s.peak_flux_jy,
        nMeasurements: s.num_images,
      }));
  }, [sources]);

  if (isLoading) {
    return <PageSkeleton variant="table" rows={8} showHeader />;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        Failed to load sources: {error.message}
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
          {selectedIds.length > 0 && (
            <span className="text-sm text-gray-500">{selectedIds.length} selected</span>
          )}
        </div>
        <div className="flex gap-2">
          {selectedIds.length > 0 && (
            <button
              type="button"
              onClick={handleExportSelected}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
            >
              Export Selected
            </button>
          )}
          <button
            type="button"
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "list"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
            onClick={() => setActiveTab("list")}
          >
            List View
          </button>
          <button
            type="button"
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "variability"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
            onClick={() => setActiveTab("variability")}
          >
            Variability Plot
          </button>
        </div>
      </div>

      {/* Advanced Query Panel */}
      <div className="mb-6">
        <AdvancedQueryPanel
          onSubmit={handleQuerySubmit}
          onReset={clearFilters}
          initialParams={queryPanelInitialParams}
          disableUrlSync
        />
      </div>

      {/* Advanced Filter Panel (collapsible) */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <button
            type="button"
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showAdvancedFilters ? "Hide Advanced Filters" : "Show Advanced Filters"}
          </button>
          {hasActiveFilters && (
            <button type="button" onClick={clearFilters} className="text-sm text-red-600 hover:text-red-800">
              Clear All Filters
            </button>
          )}
        </div>
        {showAdvancedFilters && (
          <AdvancedFilterPanel
            filters={advFilterDefs}
            values={advFilterValues}
            onChange={handleAdvFilterChange}
            onApply={() => {}}
            onReset={clearFilters}
          />
        )}
      </div>

      {/* Export Confirmation Modal */}
      <Modal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        title="Export Sources"
        size="sm"
        footer={
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowExportModal(false)}
              className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={confirmExport}
              className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700"
            >
              Export {selectedIds.length} Sources
            </button>
          </div>
        }
      >
        <p className="text-gray-600">
          You are about to export <strong>{selectedIds.length}</strong> selected sources. This will
          download a CSV file with all source data.
        </p>
      </Modal>

      {activeTab === "variability" ? (
        /* Variability Plot Tab */
        <div className="card p-4">
          {variabilityData.length > 0 ? (
            <EtaVPlot
              sources={variabilityData}
              onSourceSelect={(sourceId) => (window.location.href = `/sources/${sourceId}`)}
              height={500}
            />
          ) : (
            <p className="text-gray-500 text-center py-8">
              No variability data available. Sources need η and V values to display the variability
              plot.
            </p>
          )}
        </div>
      ) : (
        /* List View Tab */
        <>
          <p className="text-sm text-gray-500 mb-4">
            Showing {filteredCount} of {totalCount} sources
            {isFiltered && " (filtered)"}
          </p>

          {sortedData && sortedData.length > 0 ? (
            <div className="card overflow-hidden">
              <table className="table">
                <thead>
                  <tr>
                    <th className="w-10 px-3 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.length === sortedData.length && sortedData.length > 0}
                        ref={(el) => {
                          if (el)
                            el.indeterminate =
                              selectedIds.length > 0 && selectedIds.length < sortedData.length;
                        }}
                        onChange={() => {
                          if (selectedIds.length === sortedData.length) {
                            clearSourceSelection();
                          } else {
                            selectAllSources(sortedData.map((s) => s.id));
                          }
                        }}
                        className="h-4 w-4 text-blue-600 rounded"
                      />
                    </th>
                    <SortableTableHeader
                      columnKey="id"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    >
                      ID
                    </SortableTableHeader>
                    <SortableTableHeader
                      columnKey="name"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    >
                      Name
                    </SortableTableHeader>
                    <SortableTableHeader
                      columnKey="ra_deg"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                      className="text-right"
                    >
                      RA (deg)
                    </SortableTableHeader>
                    <SortableTableHeader
                      columnKey="dec_deg"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                      className="text-right"
                    >
                      Dec (deg)
                    </SortableTableHeader>
                    <SortableTableHeader
                      columnKey="num_images"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                      className="text-center"
                    >
                      Images
                    </SortableTableHeader>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {sortedData.map((source) => (
                    <tr
                      key={source.id}
                      className={selectedSources.has(source.id) ? "bg-blue-50" : ""}
                    >
                      <td className="px-3">
                        <input
                          type="checkbox"
                          checked={selectedSources.has(source.id)}
                          onChange={() => toggleSourceSelection(source.id)}
                          className="h-4 w-4 text-blue-600 rounded"
                        />
                      </td>
                      <td>
                        <Link
                          to={ROUTES.SOURCES.DETAIL(source.id)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          {source.id}
                        </Link>
                      </td>
                      <td>{source.name || "—"}</td>
                      <td className="text-right font-mono">{source.ra_deg?.toFixed(4)}</td>
                      <td className="text-right font-mono">{source.dec_deg?.toFixed(4)}</td>
                      <td className="text-center">{source.num_images ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500">No sources found.</p>
          )}
        </>
      )}
    </div>
  );
};

export default SourcesListPage;
