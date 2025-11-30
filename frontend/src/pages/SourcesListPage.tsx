import React, { useState, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { useSources } from "../hooks/useQueries";
import { LoadingSpinner, SortableTableHeader, useTableSort, Modal } from "../components/common";
import { AdvancedQueryPanel, SourceQueryParams } from "../components/query";
import { EtaVPlot, SourcePoint } from "../components/variability";
import {
  AdvancedFilterPanel,
  FilterDefinition,
  FilterValues as AdvFilterValues,
} from "../components/filters";
import { useSelectionStore } from "../stores/appStore";
import type { SourceSummary } from "../types";

/**
 * List page showing all detected sources with advanced query and variability plot.
 */
const SourcesListPage: React.FC = () => {
  const { data: sources, isLoading, error } = useSources();
  const [activeTab, setActiveTab] = useState<"list" | "variability">("list");
  const [queryParams, setQueryParams] = useState<SourceQueryParams>({});
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [advFilterValues, setAdvFilterValues] = useState<AdvFilterValues>({});
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
    const baseUrl = import.meta.env.VITE_API_URL || "/api";
    window.open(`${baseUrl}/sources/export?ids=${selectedIds.join(",")}`, "_blank");
    setShowExportModal(false);
  }, [selectedIds]);

  // Filter sources based on query params and advanced filters
  const filteredSources = useMemo(() => {
    if (!sources) return [];
    let result = sources as SourceSummary[];

    // Apply cone search filter
    if (queryParams.ra !== undefined && queryParams.dec !== undefined && queryParams.radius) {
      const { ra, dec, radius } = queryParams;
      result = result.filter((s) => {
        if (s.ra_deg === undefined || s.dec_deg === undefined) return false;
        // Simple angular distance approximation
        const dRa = (s.ra_deg - ra) * Math.cos((dec * Math.PI) / 180);
        const dDec = s.dec_deg - dec;
        const dist = Math.sqrt(dRa * dRa + dDec * dDec) * 60; // arcmin
        return dist <= radius;
      });
    }

    // Apply flux filter from queryParams
    if (queryParams.minFlux !== undefined) {
      result = result.filter((s) => (s.peak_flux_jy ?? 0) >= (queryParams.minFlux ?? 0));
    }
    if (queryParams.maxFlux !== undefined) {
      result = result.filter(
        (s) => (s.peak_flux_jy ?? Infinity) <= (queryParams.maxFlux ?? Infinity)
      );
    }

    // Apply advanced filters
    if (advFilterValues.name && typeof advFilterValues.name === "string") {
      const term = advFilterValues.name.toLowerCase();
      result = result.filter(
        (s) => s.name?.toLowerCase().includes(term) || s.id.toLowerCase().includes(term)
      );
    }
    if (advFilterValues.minImages && typeof advFilterValues.minImages === "number") {
      result = result.filter((s) => (s.num_images ?? 0) >= (advFilterValues.minImages as number));
    }
    if (advFilterValues.variable === true) {
      result = result.filter(
        (s) => s.eta !== undefined && s.v !== undefined && (s.eta > 2 || s.v > 0.1)
      );
    }

    return result;
  }, [sources, queryParams, advFilterValues]);

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
    return <LoadingSpinner label="Loading sources..." />;
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
              onClick={handleExportSelected}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
            >
              Export Selected
            </button>
          )}
          <button
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
        <AdvancedQueryPanel onQueryChange={setQueryParams} />
      </div>

      {/* Advanced Filter Panel (collapsible) */}
      <div className="mb-6">
        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className="text-sm text-blue-600 hover:text-blue-800 mb-2"
        >
          {showAdvancedFilters ? "Hide Advanced Filters" : "Show Advanced Filters"}
        </button>
        {showAdvancedFilters && (
          <AdvancedFilterPanel
            filters={advFilterDefs}
            values={advFilterValues}
            onChange={setAdvFilterValues}
            onApply={() => {}}
            onReset={() => setAdvFilterValues({})}
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
              onClick={() => setShowExportModal(false)}
              className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
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
            Showing {filteredSources.length} of {(sources as SourceSummary[])?.length ?? 0} sources
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
                          to={`/sources/${source.id}`}
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
