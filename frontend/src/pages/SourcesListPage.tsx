import React from "react";
import { Link } from "react-router-dom";
import { useSources } from "../hooks/useQueries";
import { LoadingSpinner, SortableTableHeader, useTableSort } from "../components/common";

interface Source {
  id: string;
  name?: string;
  ra_deg?: number;
  dec_deg?: number;
  num_images?: number;
}

/**
 * List page showing all detected sources.
 */
const SourcesListPage: React.FC = () => {
  const { data: sources, isLoading, error } = useSources();
  const { sortColumn, sortDirection, handleSort, sortedData } = useTableSort<Source>(
    sources as Source[] | undefined
  );

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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Sources</h1>

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
    </div>
  );
};

export default SourcesListPage;
