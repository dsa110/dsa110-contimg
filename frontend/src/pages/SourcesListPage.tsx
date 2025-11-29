import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useSources } from "../hooks/useQueries";
import { LoadingSpinner, SortableTableHeader, useTableSort } from "../components/common";
import { AdvancedQueryPanel, SourceQueryParams } from "../components/query";
import { EtaVPlot, SourcePoint } from "../components/variability";

interface Source {
  id: string;
  name?: string;
  ra_deg?: number;
  dec_deg?: number;
  num_images?: number;
  eta?: number;
  v?: number;
  peak_flux_jy?: number;
}

/**
 * List page showing all detected sources with advanced query and variability plot.
 */
const SourcesListPage: React.FC = () => {
  const { data: sources, isLoading, error } = useSources();
  const [activeTab, setActiveTab] = useState<"list" | "variability">("list");
  const [queryParams, setQueryParams] = useState<SourceQueryParams>({});

  // Filter sources based on query params
  const filteredSources = useMemo(() => {
    if (!sources) return [];
    let result = sources as Source[];

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

    // Apply flux filter
    if (queryParams.minFlux !== undefined) {
      result = result.filter((s) => (s.peak_flux_jy ?? 0) >= (queryParams.minFlux ?? 0));
    }
    if (queryParams.maxFlux !== undefined) {
      result = result.filter(
        (s) => (s.peak_flux_jy ?? Infinity) <= (queryParams.maxFlux ?? Infinity)
      );
    }

    return result;
  }, [sources, queryParams]);

  const { sortColumn, sortDirection, handleSort, sortedData } =
    useTableSort<Source>(filteredSources);

  // Build EtaVPlot data from sources
  const variabilityData: SourcePoint[] = useMemo(() => {
    if (!sources) return [];
    return (sources as Source[])
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
        <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
        <div className="flex gap-2">
          <button
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "list"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
            onClick={() => setActiveTab("list")}
          >
            📋 List View
          </button>
          <button
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "variability"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
            onClick={() => setActiveTab("variability")}
          >
            📈 Variability Plot
          </button>
        </div>
      </div>

      {/* Advanced Query Panel */}
      <div className="mb-6">
        <AdvancedQueryPanel onQueryChange={setQueryParams} />
      </div>

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
            Showing {filteredSources.length} of {(sources as Source[])?.length ?? 0} sources
          </p>

          {sortedData && sortedData.length > 0 ? (
            <div className="card overflow-hidden">
              <table className="table">
                <thead>
                  <tr>
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
                    <tr key={source.id}>
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
